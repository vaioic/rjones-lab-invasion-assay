from shared import core

core.process_directory(r"../data/20x", r"../processed/2026-10-05")

# # mask = core.segment_nuclei(
# #     r"../data/20x/SMG253_A1-02_processed.czi", r"../processed/2026-10-05 Dev"
# # )
# cnt = core.count_nuclei(
#     r"../data/20x/SMG253_B6-01_processed.czi", r"../processed/2026-10-05 Dev"
# )
