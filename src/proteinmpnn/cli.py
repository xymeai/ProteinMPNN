import argparse

__all__ = ["argparser"]

argparser = argparse.ArgumentParser(
    formatter_class=argparse.ArgumentDefaultsHelpFormatter
)

argparser.add_argument(
    "--suppress_print", type=int, default=0, help="0 for False, 1 for True"
)

argparser.add_argument(
    "--ca_only",
    action="store_true",
    default=False,
    help="Parse CA-only structures and use CA-only models (default: false)",
)
argparser.add_argument(
    "--path_to_model_weights",
    type=str,
    default="",
    help="Path to model weights folder;",
)
argparser.add_argument(
    "--model_name",
    type=str,
    default="v_48_020",
    help="ProteinMPNN model name: v_48_002, v_48_010, v_48_020, v_48_030; "
    "v_48_010=version with 48 edges 0.10A noise",
)
argparser.add_argument(
    "--use_soluble_model",
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
    "--save_score",
    type=int,
    default=0,
    help="0 for False, 1 for True; save score=-log_prob to npy files",
)
argparser.add_argument(
    "--save_probs",
    type=int,
    default=0,
    help="0 for False, 1 for True; save MPNN predicted probabilites per position",
)

argparser.add_argument(
    "--score_only",
    type=int,
    default=0,
    help="0 for False, 1 for True; score input backbone-sequence pairs",
)
argparser.add_argument(
    "--path_to_fasta",
    type=str,
    default="",
    help="score provided input sequence in a fasta format; e.g. GGGGGG/PPPPS/WWW for "
    "chains A, B, C sorted alphabetically and separated by /",
)

argparser.add_argument(
    "--conditional_probs_only",
    type=int,
    default=0,
    help="0 for False, 1 for True; output conditional probabilities p(s_i given the "
    "rest of the sequence and backbone)",
)
argparser.add_argument(
    "--conditional_probs_only_backbone",
    type=int,
    default=0,
    help="0 for False, 1 for True; if true output conditional probabilities p(s_i "
    "given backbone)",
)
argparser.add_argument(
    "--unconditional_probs_only",
    type=int,
    default=0,
    help="0 for False, 1 for True; output unconditional probabilities p(s_i given "
    "backbone) in one forward pass",
)

argparser.add_argument(
    "--backbone_noise",
    type=float,
    default=0.00,
    help="Standard deviation of Gaussian noise to add to backbone atoms",
)
argparser.add_argument(
    "--num_seq_per_target",
    type=int,
    default=1,
    help="Number of sequences to generate per target",
)
argparser.add_argument(
    "--batch_size",
    type=int,
    default=1,
    help="Batch size; can set higher for titan, quadro GPUs, reduce this if running "
    "out of GPU memory",
)
argparser.add_argument(
    "--max_length", type=int, default=200000, help="Max sequence length"
)
argparser.add_argument(
    "--sampling_temp",
    type=str,
    default="0.1",
    help="A string of temperatures, 0.2 0.25 0.5. Sampling temperature for amino "
    "acids. Suggested values 0.1, 0.15, 0.2, 0.25, 0.3. Higher values will lead "
    "to more diversity.",
)

argparser.add_argument(
    "--out_folder",
    type=str,
    help="Path to a folder to output sequences, e.g. /home/out/",
)
argparser.add_argument(
    "--pdb_path", type=str, default="", help="Path to a single PDB to be designed"
)
argparser.add_argument(
    "--pdb_path_chains",
    type=str,
    default="",
    help="Define which chains need to be designed for a single PDB ",
)
argparser.add_argument(
    "--jsonl_path", type=str, help="Path to a folder with parsed pdb into jsonl"
)
argparser.add_argument(
    "--chain_id_jsonl",
    type=str,
    default="",
    help="Path to a dictionary specifying which chains need to be designed and which "
    "ones are fixed, if not specied all chains will be designed.",
)
argparser.add_argument(
    "--fixed_positions_jsonl",
    type=str,
    default="",
    help="Path to a dictionary with fixed positions",
)
argparser.add_argument(
    "--omit_AAs",
    type=list,
    default="X",
    help="Specify which amino acids should be omitted in the generated sequence, "
    "e.g. 'AC' would omit alanine and cystine.",
)
argparser.add_argument(
    "--bias_AA_jsonl",
    type=str,
    default="",
    help="Path to a dictionary which specifies AA composion bias if neededi, e.g. "
    "{A: -1.1, F: 0.7} would make A less likely and F more likely.",
)

argparser.add_argument(
    "--bias_by_res_jsonl",
    default="",
    help="Path to dictionary with per position bias.",
)
argparser.add_argument(
    "--omit_AA_jsonl",
    type=str,
    default="",
    help="Path to a dictionary which specifies which amino acids need to be omitted "
    "from design at specific chain indices",
)
argparser.add_argument(
    "--pssm_jsonl", type=str, default="", help="Path to a dictionary with pssm"
)
argparser.add_argument(
    "--pssm_multi",
    type=float,
    default=0.0,
    help="A value between [0.0, 1.0], 0.0 means do not use pssm, 1.0 ignore MPNN "
    "predictions",
)
argparser.add_argument(
    "--pssm_threshold",
    type=float,
    default=0.0,
    help="A value between -inf + inf to restric per position AAs",
)
argparser.add_argument(
    "--pssm_log_odds_flag", type=int, default=0, help="0 for False, 1 for True"
)
argparser.add_argument(
    "--pssm_bias_flag", type=int, default=0, help="0 for False, 1 for True"
)

argparser.add_argument(
    "--tied_positions_jsonl",
    type=str,
    default="",
    help="Path to a dictionary with tied positions",
)
