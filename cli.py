import argparse

__all__ = ["argparser"]

argparser = argparse.ArgumentParser(
    prog="ProteinMPNN",
    description="Robust deep learning--based protein sequence design using ProteinMPNN",
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
    help="score provided input sequence in a fasta format; e.g. GGGGGG/PPPPS/WWW for "
    "chains A, B, C sorted alphabetically and separated by /",
)

argparser.add_argument(
    "--conditional-probs-only",
    type=int,
    default=0,
    help="0 for False, 1 for True; output conditional probabilities p(s_i given the "
    "rest of the sequence and backbone)",
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
    help="Batch size; can set higher for titan, quadro GPUs, reduce this if running "
    "out of GPU memory",
)
argparser.add_argument(
    "--max-length", type=int, default=200000, help="Max sequence length"
)
argparser.add_argument(
    "--sampling-temp",
    type=str,
    default="0.1",
    help="A string of temperatures, 0.2 0.25 0.5. Sampling temperature for amino "
    "acids. Suggested values 0.1, 0.15, 0.2, 0.25, 0.3. Higher values will lead "
    "to more diversity.",
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
    help="Path to a dictionary specifying which chains need to be designed and which "
    "ones are fixed, if not specied all chains will be designed.",
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
    help="Path to a dictionary which specifies AA composion bias if neededi, e.g. "
    "{A: -1.1, F: 0.7} would make A less likely and F more likely.",
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
    help="Path to a dictionary which specifies which amino acids need to be omitted "
    "from design at specific chain indices",
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
