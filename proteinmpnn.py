import argparse
import copy
import json
import logging
import os
import random
import sys
import time

import numpy as np
import torch

from utils import (
    ProteinMPNN,
    StructureDataset,
    StructureDatasetPDB,
    _S_to_seq,
    _scores,
    parse_fasta,
    parse_PDB,
    tied_featurize,
)

logger = logging.getLogger(__name__)


def main(args):
    """ """
    logging.basicConfig(
        encoding="utf-8",
        level=logging.INFO,
        format="ProteinMPNN - %(levelname)-7s - %(message)s",
    )

    if args.seed:
        seed = args.seed
    else:
        seed = int(np.random.randint(0, high=999, size=1, dtype=int)[0])

    torch.manual_seed(seed)
    random.seed(seed)
    np.random.seed(seed)

    hidden_dim = 128
    num_layers = 3

    package_root_dir = os.path.abspath(os.path.dirname(__file__))

    if args.path_to_model_weights:
        model_folder_path = args.path_to_model_weights

        if model_folder_path[-1] != "/":
            model_folder_path = model_folder_path + "/"

    # custom path to directory containing model weights has not been given
    else:
        file_path = os.path.join(package_root_dir, "data", "weights")

        # Use CA-only model weights
        if args.ca_only:
            logger.info("Using CA-ProteinMPNN!")
            model_folder_path = os.path.join(file_path, "ca_model_weights")

            if args.use_soluble_model:
                logger.info("WARNING: CA-SolubleMPNN is not available yet")
                sys.exit()
        else:
            if args.use_soluble_model:
                logger.info("Using ProteinMPNN trained on soluble proteins only!")
                model_folder_path = os.path.join(file_path, "soluble_model_weights")
            else:
                model_folder_path = os.path.join(file_path, "vanilla_model_weights")

    checkpoint_path = os.path.join(model_folder_path, f"{args.model_name}.pt")
    folder_for_outputs = args.out_folder

    NUM_BATCHES = args.num_seq_per_target // args.batch_size
    BATCH_COPIES = args.batch_size

    temperatures = [float(item) for item in args.sampling_temp.split()]
    omit_AAs_list = args.omit_AAs
    alphabet = "ACDEFGHIKLMNPQRSTVWYX"
    alphabet_dict = dict(zip(alphabet, range(21), strict=False))
    print_all = args.suppress_print == 0
    omit_AAs_np = np.array([AA in omit_AAs_list for AA in alphabet]).astype(np.float32)
    device = torch.device("cuda:0" if (torch.cuda.is_available()) else "cpu")

    if os.path.isfile(args.chain_id_jsonl):
        with open(args.chain_id_jsonl) as json_file:
            json_list = list(json_file)
        for json_str in json_list:
            chain_id_dict = json.loads(json_str)
    else:
        chain_id_dict = None
        logger.debug("chain_id_jsonl is NOT loaded")

    if os.path.isfile(args.fixed_positions_jsonl):
        with open(args.fixed_positions_jsonl) as json_file:
            json_list = list(json_file)
        for json_str in json_list:
            fixed_positions_dict = json.loads(json_str)
    else:
        logger.debug("fixed_positions_jsonl is NOT loaded")
        fixed_positions_dict = None

    if os.path.isfile(args.pssm_jsonl):
        with open(args.pssm_jsonl) as json_file:
            json_list = list(json_file)
        pssm_dict = {}
        for json_str in json_list:
            pssm_dict.update(json.loads(json_str))
    else:
        logger.debug("pssm_jsonl is NOT loaded")
        pssm_dict = None

    if os.path.isfile(args.omit_AA_jsonl):
        with open(args.omit_AA_jsonl) as json_file:
            json_list = list(json_file)
        for json_str in json_list:
            omit_AA_dict = json.loads(json_str)
    else:
        logger.debug("omit_AA_jsonl is NOT loaded")
        omit_AA_dict = None

    if os.path.isfile(args.bias_AA_jsonl):
        with open(args.bias_AA_jsonl) as json_file:
            json_list = list(json_file)
        for json_str in json_list:
            bias_AA_dict = json.loads(json_str)
    else:
        logger.debug("bias_AA_jsonl is NOT loaded")
        bias_AA_dict = None

    if os.path.isfile(args.tied_positions_jsonl):
        with open(args.tied_positions_jsonl) as json_file:
            json_list = list(json_file)
        for json_str in json_list:
            tied_positions_dict = json.loads(json_str)
    else:
        logger.debug("tied_positions_jsonl is NOT loaded")
        tied_positions_dict = None

    if os.path.isfile(args.bias_by_res_jsonl):
        with open(args.bias_by_res_jsonl) as json_file:
            json_list = list(json_file)

        for json_str in json_list:
            bias_by_res_dict = json.loads(json_str)

        logger.debug("bias by residue dictionary is loaded")
    else:
        logger.debug("bias by residue dictionary is not loaded, or not provided")
        bias_by_res_dict = None

    bias_AAs_np = np.zeros(len(alphabet))

    if bias_AA_dict:
        for n, AA in enumerate(alphabet):
            if AA in list(bias_AA_dict.keys()):
                bias_AAs_np[n] = bias_AA_dict[AA]

    if args.pdb_path:
        pdb_dict_list = parse_PDB(args.pdb_path, ca_only=args.ca_only)
        dataset_valid = StructureDatasetPDB(
            pdb_dict_list, truncate=None, max_length=args.max_length
        )
        all_chain_list = [
            item[-1:] for item in list(pdb_dict_list[0]) if item[:9] == "seq_chain"
        ]  # ['A','B', 'C',...]
        if args.pdb_path_chains:
            designed_chain_list = [str(item) for item in args.pdb_path_chains.split()]
        else:
            designed_chain_list = all_chain_list
        fixed_chain_list = [
            letter for letter in all_chain_list if letter not in designed_chain_list
        ]
        chain_id_dict = {}
        chain_id_dict[pdb_dict_list[0]["name"]] = (
            designed_chain_list,
            fixed_chain_list,
        )
    else:
        dataset_valid = StructureDataset(
            args.jsonl_path,
            truncate=None,
            max_length=args.max_length,
            verbose=True,
        )

    checkpoint = torch.load(checkpoint_path, map_location=device)
    noise_level_print = checkpoint["noise_level"]

    model = ProteinMPNN(
        ca_only=args.ca_only,
        num_letters=21,
        node_features=hidden_dim,
        edge_features=hidden_dim,
        hidden_dim=hidden_dim,
        num_encoder_layers=num_layers,
        num_decoder_layers=num_layers,
        augment_eps=args.backbone_noise,
        k_neighbors=checkpoint["num_edges"],
    )

    model.to(device)
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()

    logger.warning("Number of edges: %s", checkpoint["num_edges"])
    logger.warning("Training noise level: %sA", noise_level_print)

    # Build paths for experiment
    base_folder = folder_for_outputs

    if base_folder[-1] != "/":
        base_folder = base_folder + "/"
    if not os.path.exists(base_folder):
        os.makedirs(base_folder)

    if not os.path.exists(base_folder + "seqs"):
        os.makedirs(base_folder + "seqs")

    if args.save_score:
        if not os.path.exists(base_folder + "scores"):
            os.makedirs(base_folder + "scores")

    if args.score_only:
        if not os.path.exists(base_folder + "score_only"):
            os.makedirs(base_folder + "score_only")

    if args.conditional_probs_only:
        if not os.path.exists(base_folder + "conditional_probs_only"):
            os.makedirs(base_folder + "conditional_probs_only")

    if args.unconditional_probs_only:
        if not os.path.exists(base_folder + "unconditional_probs_only"):
            os.makedirs(base_folder + "unconditional_probs_only")

    if args.save_probs:
        if not os.path.exists(base_folder + "probs"):
            os.makedirs(base_folder + "probs")

    # Validation epoch
    with torch.no_grad():
        for ix, protein in enumerate(dataset_valid):
            score_list = []
            global_score_list = []
            all_probs_list = []
            all_log_probs_list = []
            S_sample_list = []
            batch_clones = [copy.deepcopy(protein) for i in range(BATCH_COPIES)]
            (
                X,
                S,
                mask,
                lengths,
                chain_M,
                chain_encoding_all,
                chain_list_list,
                visible_list_list,
                masked_list_list,
                masked_chain_length_list_list,
                chain_M_pos,
                omit_AA_mask,
                residue_idx,
                dihedral_mask,
                tied_pos_list_of_lists_list,
                pssm_coef,
                pssm_bias,
                pssm_log_odds_all,
                bias_by_res_all,
                tied_beta,
            ) = tied_featurize(
                batch_clones,
                device,
                chain_id_dict,
                fixed_positions_dict,
                omit_AA_dict,
                tied_positions_dict,
                pssm_dict,
                bias_by_res_dict,
                ca_only=args.ca_only,
            )
            pssm_log_odds_mask = (
                pssm_log_odds_all > args.pssm_threshold
            ).float()  # 1.0 for true, 0.0 for false
            name_ = batch_clones[0]["name"]

            if args.score_only:
                loop_c = 0
                if args.path_to_fasta:
                    fasta_names, fasta_seqs = parse_fasta(
                        args.path_to_fasta, omit=["/"]
                    )
                    loop_c = len(fasta_seqs)
                for fc in range(1 + loop_c):
                    if fc == 0:
                        structure_sequence_score_file = (
                            base_folder
                            + "/score_only/"
                            + batch_clones[0]["name"]
                            + "_pdb"
                        )
                    else:
                        structure_sequence_score_file = (
                            base_folder
                            + "/score_only/"
                            + batch_clones[0]["name"]
                            + f"_fasta_{fc}"
                        )
                    native_score_list = []
                    global_native_score_list = []
                    if fc > 0:
                        input_seq_length = len(fasta_seqs[fc - 1])
                        S_input = torch.tensor(
                            [alphabet_dict[AA] for AA in fasta_seqs[fc - 1]],
                            device=device,
                        )[None, :].repeat(X.shape[0], 1)
                        S[:, :input_seq_length] = (
                            S_input  # assumes that S and S_input are alphabetically sorted for masked_chains
                        )
                    for j in range(NUM_BATCHES):
                        randn_1 = torch.randn(chain_M.shape, device=X.device)
                        log_probs = model(
                            X,
                            S,
                            mask,
                            chain_M * chain_M_pos,
                            residue_idx,
                            chain_encoding_all,
                            randn_1,
                        )
                        mask_for_loss = mask * chain_M * chain_M_pos
                        scores = _scores(S, log_probs, mask_for_loss)
                        native_score = scores.cpu().data.numpy()
                        native_score_list.append(native_score)
                        global_scores = _scores(S, log_probs, mask)
                        global_native_score = global_scores.cpu().data.numpy()
                        global_native_score_list.append(global_native_score)
                    native_score = np.concatenate(native_score_list, 0)
                    global_native_score = np.concatenate(global_native_score_list, 0)
                    ns_mean = native_score.mean()
                    ns_mean_print = np.format_float_positional(
                        np.float32(ns_mean), unique=False, precision=4
                    )
                    ns_std = native_score.std()
                    ns_std_print = np.format_float_positional(
                        np.float32(ns_std), unique=False, precision=4
                    )

                    global_ns_mean = global_native_score.mean()
                    global_ns_mean_print = np.format_float_positional(
                        np.float32(global_ns_mean), unique=False, precision=4
                    )
                    global_ns_std = global_native_score.std()
                    global_ns_std_print = np.format_float_positional(
                        np.float32(global_ns_std), unique=False, precision=4
                    )

                    ns_sample_size = native_score.shape[0]
                    seq_str = _S_to_seq(S[0,], chain_M[0,])
                    np.savez(
                        structure_sequence_score_file,
                        score=native_score,
                        global_score=global_native_score,
                        S=S[0,].cpu().numpy(),
                        seq_str=seq_str,
                    )
                    if fc == 0:
                        logger.info(
                            f"Score for {name_} from PDB, mean: {ns_mean_print}, std: {ns_std_print}, sample size: {ns_sample_size},  global score, mean: {global_ns_mean_print}, std: {global_ns_std_print}, sample size: {ns_sample_size}"
                        )
                    else:
                        logger.info(
                            f"Score for {name_}_{fc} from FASTA, mean: {ns_mean_print}, std: {ns_std_print}, sample size: {ns_sample_size},  global score, mean: {global_ns_mean_print}, std: {global_ns_std_print}, sample size: {ns_sample_size}"
                        )
            elif args.conditional_probs_only:
                logger.info("Calculating conditional probabilities for %s.", name_)
                conditional_probs_only_file = (
                    base_folder + "/conditional_probs_only/" + batch_clones[0]["name"]
                )
                log_conditional_probs_list = []

                for j in range(NUM_BATCHES):
                    randn_1 = torch.randn(chain_M.shape, device=X.device)
                    log_conditional_probs = model.conditional_probs(
                        X,
                        S,
                        mask,
                        chain_M * chain_M_pos,
                        residue_idx,
                        chain_encoding_all,
                        randn_1,
                        args.conditional_probs_only_backbone,
                    )
                    log_conditional_probs_list.append(
                        log_conditional_probs.cpu().numpy()
                    )
                concat_log_p = np.concatenate(
                    log_conditional_probs_list, 0
                )  # [B, L, 21]
                mask_out = (chain_M * chain_M_pos * mask)[0,].cpu().numpy()
                np.savez(
                    conditional_probs_only_file,
                    log_p=concat_log_p,
                    S=S[0,].cpu().numpy(),
                    mask=mask[0,].cpu().numpy(),
                    design_mask=mask_out,
                )
            elif args.unconditional_probs_only:
                logger.info(f"Calculating unconditional probabilities for {name_}")

                unconditional_probs_only_file = (
                    base_folder + "/unconditional_probs_only/" + batch_clones[0]["name"]
                )
                log_unconditional_probs_list = []
                for j in range(NUM_BATCHES):
                    log_unconditional_probs = model.unconditional_probs(
                        X, mask, residue_idx, chain_encoding_all
                    )
                    log_unconditional_probs_list.append(
                        log_unconditional_probs.cpu().numpy()
                    )
                concat_log_p = np.concatenate(
                    log_unconditional_probs_list, 0
                )  # [B, L, 21]
                mask_out = (chain_M * chain_M_pos * mask)[0,].cpu().numpy()
                np.savez(
                    unconditional_probs_only_file,
                    log_p=concat_log_p,
                    S=S[0,].cpu().numpy(),
                    mask=mask[0,].cpu().numpy(),
                    design_mask=mask_out,
                )
            else:
                randn_1 = torch.randn(chain_M.shape, device=X.device)
                log_probs = model(
                    X,
                    S,
                    mask,
                    chain_M * chain_M_pos,
                    residue_idx,
                    chain_encoding_all,
                    randn_1,
                )
                mask_for_loss = mask * chain_M * chain_M_pos

                # score only the redesigned part
                scores = _scores(S, log_probs, mask_for_loss)
                native_score = scores.cpu().data.numpy()
                global_scores = _scores(S, log_probs, mask)

                # score the whole structure-sequence
                global_native_score = global_scores.cpu().data.numpy()

                # Generate some sequences
                ali_file = base_folder + "/seqs/" + batch_clones[0]["name"] + ".fa"
                score_file = base_folder + "/scores/" + batch_clones[0]["name"] + ".npz"
                probs_file = base_folder + "/probs/" + batch_clones[0]["name"] + ".npz"

                logger.info("Generating sequences for: %s", name_)

                t0 = time.time()

                with open(ali_file, "w") as f:
                    for temp in temperatures:
                        for j in range(NUM_BATCHES):
                            randn_2 = torch.randn(chain_M.shape, device=X.device)
                            if tied_positions_dict is None:
                                sample_dict = model.sample(
                                    X,
                                    randn_2,
                                    S,
                                    chain_M,
                                    chain_encoding_all,
                                    residue_idx,
                                    mask=mask,
                                    temperature=temp,
                                    omit_AAs_np=omit_AAs_np,
                                    bias_AAs_np=bias_AAs_np,
                                    chain_M_pos=chain_M_pos,
                                    omit_AA_mask=omit_AA_mask,
                                    pssm_coef=pssm_coef,
                                    pssm_bias=pssm_bias,
                                    pssm_multi=args.pssm_multi,
                                    pssm_log_odds_flag=bool(args.pssm_log_odds_flag),
                                    pssm_log_odds_mask=pssm_log_odds_mask,
                                    pssm_bias_flag=bool(args.pssm_bias_flag),
                                    bias_by_res=bias_by_res_all,
                                )
                                S_sample = sample_dict["S"]
                            else:
                                sample_dict = model.tied_sample(
                                    X,
                                    randn_2,
                                    S,
                                    chain_M,
                                    chain_encoding_all,
                                    residue_idx,
                                    mask=mask,
                                    temperature=temp,
                                    omit_AAs_np=omit_AAs_np,
                                    bias_AAs_np=bias_AAs_np,
                                    chain_M_pos=chain_M_pos,
                                    omit_AA_mask=omit_AA_mask,
                                    pssm_coef=pssm_coef,
                                    pssm_bias=pssm_bias,
                                    pssm_multi=args.pssm_multi,
                                    pssm_log_odds_flag=bool(args.pssm_log_odds_flag),
                                    pssm_log_odds_mask=pssm_log_odds_mask,
                                    pssm_bias_flag=bool(args.pssm_bias_flag),
                                    tied_pos=tied_pos_list_of_lists_list[0],
                                    tied_beta=tied_beta,
                                    bias_by_res=bias_by_res_all,
                                )
                                # Compute scores
                                S_sample = sample_dict["S"]

                            log_probs = model(
                                X,
                                S_sample,
                                mask,
                                chain_M * chain_M_pos,
                                residue_idx,
                                chain_encoding_all,
                                randn_2,
                                use_input_decoding_order=True,
                                decoding_order=sample_dict["decoding_order"],
                            )

                            mask_for_loss = mask * chain_M * chain_M_pos
                            scores = _scores(S_sample, log_probs, mask_for_loss)
                            scores = scores.cpu().data.numpy()

                            # score the whole structure-sequence
                            global_scores = _scores(S_sample, log_probs, mask)
                            global_scores = global_scores.cpu().data.numpy()

                            all_probs_list.append(
                                sample_dict["probs"].cpu().data.numpy()
                            )
                            all_log_probs_list.append(log_probs.cpu().data.numpy())
                            S_sample_list.append(S_sample.cpu().data.numpy())

                            for b_ix in range(BATCH_COPIES):
                                masked_chain_length_list = (
                                    masked_chain_length_list_list[b_ix]
                                )
                                masked_list = masked_list_list[b_ix]
                                seq_recovery_rate = torch.sum(
                                    torch.sum(
                                        torch.nn.functional.one_hot(S[b_ix], 21)
                                        * torch.nn.functional.one_hot(
                                            S_sample[b_ix], 21
                                        ),
                                        axis=-1,
                                    )
                                    * mask_for_loss[b_ix]
                                ) / torch.sum(mask_for_loss[b_ix])
                                seq = _S_to_seq(S_sample[b_ix], chain_M[b_ix])
                                score = scores[b_ix]
                                score_list.append(score)
                                global_score = global_scores[b_ix]
                                global_score_list.append(global_score)
                                native_seq = _S_to_seq(S[b_ix], chain_M[b_ix])

                                if b_ix == 0 and j == 0 and temp == temperatures[0]:
                                    start = 0
                                    end = 0
                                    list_of_AAs = []
                                    for mask_l in masked_chain_length_list:
                                        end += mask_l
                                        list_of_AAs.append(native_seq[start:end])
                                        start = end
                                    native_seq = "".join(
                                        list(
                                            np.array(list_of_AAs)[
                                                np.argsort(masked_list)
                                            ]
                                        )
                                    )
                                    l0 = 0

                                    for mc_length in list(
                                        np.array(masked_chain_length_list)[
                                            np.argsort(masked_list)
                                        ]
                                    )[:-1]:
                                        l0 += mc_length
                                        native_seq = (
                                            native_seq[:l0] + "/" + native_seq[l0:]
                                        )
                                        l0 += 1
                                    sorted_masked_chain_letters = np.argsort(
                                        masked_list_list[0]
                                    )
                                    print_masked_chains = [
                                        masked_list_list[0][i]
                                        for i in sorted_masked_chain_letters
                                    ]
                                    sorted_visible_chain_letters = np.argsort(
                                        visible_list_list[0]
                                    )
                                    print_visible_chains = [
                                        visible_list_list[0][i]
                                        for i in sorted_visible_chain_letters
                                    ]
                                    native_score_print = np.format_float_positional(
                                        np.float32(native_score.mean()),
                                        unique=False,
                                        precision=4,
                                    )
                                    global_native_score_print = (
                                        np.format_float_positional(
                                            np.float32(global_native_score.mean()),
                                            unique=False,
                                            precision=4,
                                        )
                                    )

                                    if args.ca_only:
                                        print_model_name = "CA_model_name"
                                    else:
                                        print_model_name = "model_name"

                                    f.write(
                                        f">{name_}, score={native_score_print}, global_score={global_native_score_print}, fixed_chains={print_visible_chains}, designed_chains={print_masked_chains}, {print_model_name}={args.model_name}, seed={seed}\n{native_seq}\n"
                                    )  # write the native sequence
                                start = 0
                                end = 0
                                list_of_AAs = []
                                for mask_l in masked_chain_length_list:
                                    end += mask_l
                                    list_of_AAs.append(seq[start:end])
                                    start = end

                                seq = "".join(
                                    list(np.array(list_of_AAs)[np.argsort(masked_list)])
                                )
                                l0 = 0
                                for mc_length in list(
                                    np.array(masked_chain_length_list)[
                                        np.argsort(masked_list)
                                    ]
                                )[:-1]:
                                    l0 += mc_length
                                    seq = seq[:l0] + "/" + seq[l0:]
                                    l0 += 1
                                score_print = np.format_float_positional(
                                    np.float32(score), unique=False, precision=4
                                )
                                global_score_print = np.format_float_positional(
                                    np.float32(global_score), unique=False, precision=4
                                )
                                seq_rec_print = np.format_float_positional(
                                    np.float32(
                                        seq_recovery_rate.detach().cpu().numpy()
                                    ),
                                    unique=False,
                                    precision=4,
                                )
                                sample_number = j * BATCH_COPIES + b_ix + 1
                                f.write(
                                    f">T={temp}, sample={sample_number}, score={score_print}, global_score={global_score_print}, seq_recovery={seq_rec_print}\n{seq}\n"
                                )  # write generated sequence
                if args.save_score:
                    np.savez(
                        score_file,
                        score=np.array(score_list, np.float32),
                        global_score=np.array(global_score_list, np.float32),
                    )
                if args.save_probs:
                    all_probs_concat = np.concatenate(all_probs_list)
                    all_log_probs_concat = np.concatenate(all_log_probs_list)
                    S_sample_concat = np.concatenate(S_sample_list)
                    np.savez(
                        probs_file,
                        probs=np.array(all_probs_concat, np.float32),
                        log_probs=np.array(all_log_probs_concat, np.float32),
                        S=np.array(S_sample_concat, np.int32),
                        mask=mask_for_loss.cpu().data.numpy(),
                        chain_order=chain_list_list,
                    )
                t1 = time.time()
                dt = round(float(t1 - t0), 4)
                num_seqs = len(temperatures) * NUM_BATCHES * BATCH_COPIES
                total_length = X.shape[1]

                logger.info(
                    "%s sequences of length %s generated in %s seconds",
                    num_seqs,
                    total_length,
                    dt,
                )


if __name__ == "__main__":
    argparser = argparse.ArgumentParser(
        prog="ProteinMPNN",
        description="Robust deep learning--based protein sequence design using "
        "ProteinMPNN",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    argparser.add_argument(
        "--suppress-print", type=int, default=0, help="0 for False, 1 for True"
    )

    argparser.add_argument(
        "--ca-only",
        action="store_true",
        default=False,
        help="Parse CA-only structures and use CA-only models (default: false)",
    )
    argparser.add_argument(
        "--path-to-model-weights",
        type=str,
        default="",
        help="Path to model weights folder;",
    )
    argparser.add_argument(
        "--model-name",
        type=str,
        default="v_48_020",
        help="ProteinMPNN model name: v_48_002, v_48_010, v_48_020, v_48_030; "
        "v_48_010=version with 48 edges 0.10A noise",
    )
    argparser.add_argument(
        "--use-soluble-model",
        action="store_true",
        default=False,
        help="Flag to load ProteinMPNN weights trained on soluble proteins only.",
    )

    argparser.add_argument(
        "--seed",
        type=int,
        default=0,
        help="If set to 0 then a random seed will be picked;",
    )

    argparser.add_argument(
        "--save-score",
        type=int,
        default=0,
        help="0 for False, 1 for True; save score=-log_prob to npy files",
    )
    argparser.add_argument(
        "--save-probs",
        type=int,
        default=0,
        help="0 for False, 1 for True; save MPNN predicted probabilites per position",
    )

    argparser.add_argument(
        "--score-only",
        type=int,
        default=0,
        help="0 for False, 1 for True; score input backbone-sequence pairs",
    )
    argparser.add_argument(
        "--path-to-fasta",
        type=str,
        default="",
        help="score provided input sequence in a fasta format; e.g. GGGGGG/PPPPS/WWW "
        "for chains A, B, C sorted alphabetically and separated by /",
    )

    argparser.add_argument(
        "--conditional-probs-only",
        type=int,
        default=0,
        help="0 for False, 1 for True; output conditional probabilities p(s_i given "
        "the rest of the sequence and backbone)",
    )
    argparser.add_argument(
        "--conditional-probs-only-backbone",
        type=int,
        default=0,
        help="0 for False, 1 for True; if true output conditional probabilities p(s_i "
        "given backbone)",
    )
    argparser.add_argument(
        "--unconditional-probs-only",
        type=int,
        default=0,
        help="0 for False, 1 for True; output unconditional probabilities p(s_i given "
        "backbone) in one forward pass",
    )

    argparser.add_argument(
        "--backbone-noise",
        type=float,
        default=0.00,
        help="Standard deviation of Gaussian noise to add to backbone atoms",
    )
    argparser.add_argument(
        "--num-seq-per-target",
        type=int,
        default=1,
        help="Number of sequences to generate per target",
    )
    argparser.add_argument(
        "--batch-size",
        type=int,
        default=1,
        help="Batch size; can set higher for titan, quadro GPUs, reduce this if "
        "running out of GPU memory",
    )
    argparser.add_argument(
        "--max-length", type=int, default=200000, help="Max sequence length"
    )
    argparser.add_argument(
        "--sampling-temp",
        type=str,
        default="0.1",
        help="A string of temperatures, 0.2 0.25 0.5. Sampling temperature for amino "
        "acids. Suggested values 0.1, 0.15, 0.2, 0.25, 0.3. Higher values will "
        "lead to more diversity.",
    )

    argparser.add_argument(
        "--out-folder",
        type=str,
        help="Path to a folder to output sequences, e.g. /home/out/",
    )
    argparser.add_argument(
        "--pdb-path", type=str, default="", help="Path to a single PDB to be designed"
    )
    argparser.add_argument(
        "--pdb-path-chains",
        type=str,
        default="",
        help="Define which chains need to be designed for a single PDB ",
    )
    argparser.add_argument(
        "--jsonl-path", type=str, help="Path to a folder with parsed pdb into jsonl"
    )
    argparser.add_argument(
        "--chain-id-jsonl",
        type=str,
        default="",
        help="Path to a dictionary specifying which chains need to be designed and "
        "which ones are fixed, if not specied all chains will be designed.",
    )
    argparser.add_argument(
        "--fixed-positions-jsonl",
        type=str,
        default="",
        help="Path to a dictionary with fixed positions",
    )
    argparser.add_argument(
        "--omit-AAs",
        type=list,
        default="X",
        help="Specify which amino acids should be omitted in the generated sequence, "
        "e.g. 'AC' would omit alanine and cystine.",
    )
    argparser.add_argument(
        "--bias-AA-jsonl",
        type=str,
        default="",
        help="Path to a dictionary which specifies AA composition bias if needed, "
        "e.g. {A: -1.1, F: 0.7} would make A less likely and F more likely.",
    )

    argparser.add_argument(
        "--bias-by-res-jsonl",
        default="",
        help="Path to dictionary with per position bias.",
    )
    argparser.add_argument(
        "--omit-AA-jsonl",
        type=str,
        default="",
        help="Path to a dictionary which specifies which amino acids need to be "
        "omitted from design at specific chain indices",
    )
    argparser.add_argument(
        "--pssm-jsonl", type=str, default="", help="Path to a dictionary with pssm"
    )
    argparser.add_argument(
        "--pssm-multi",
        type=float,
        default=0.0,
        help="A value between [0.0, 1.0], 0.0 means do not use pssm, 1.0 ignore MPNN "
        "predictions",
    )
    argparser.add_argument(
        "--pssm-threshold",
        type=float,
        default=0.0,
        help="A value between -inf + inf to restric per position AAs",
    )
    argparser.add_argument(
        "--pssm-log-odds-flag", type=int, default=0, help="0 for False, 1 for True"
    )
    argparser.add_argument(
        "--pssm-bias_flag", type=int, default=0, help="0 for False, 1 for True"
    )

    argparser.add_argument(
        "--tied-positions-jsonl",
        type=str,
        default="",
        help="Path to a dictionary with tied positions",
    )

    args = argparser.parse_args(args=None if sys.argv[1:] else ["--help"])
    main(args)