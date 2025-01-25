# from dataclasses import dataclass
# from typing import Dict, List, Set, Tuple, Optional, Any
# import pandas as pd
# import numpy as np
# from collections import defaultdict
# import logging
# from datetime import datetime
# import time
# from tabulate import tabulate
# import colorama
# from colorama import Fore, Style
# from concurrent.futures import ThreadPoolExecutor
# import hashlib
# from itertools import combinations
# import multiprocessing
# from datasketch import MinHash, MinHashLSH
# import re

# colorama.init()


# @dataclass
# class DuplicateResult:
#     """Structure to hold duplicate detection results"""
#     row_pairs: List[Tuple[int, int]]
#     similarity: float
#     pattern: str
#     differences: Optional[Dict[str, Tuple[Any, Any]]] = None


# class DuplicateDetector:
#     def __init__(
#             self,
#             near_match_threshold: float = 0.3,
#             num_perm: int = 128,
#             n_jobs: int = -1,
#             blocking_columns: Optional[List[str]] = None
#     ):
#         self.near_match_threshold = near_match_threshold
#         self.num_perm = num_perm
#         self.n_jobs = n_jobs if n_jobs > 0 else max(1, multiprocessing.cpu_count())
#         self.blocking_columns = blocking_columns
#         self.logger = self._setup_logger()
#         self.lsh = MinHashLSH(threshold=near_match_threshold, num_perm=num_perm)

#     def _setup_logger(self) -> logging.Logger:
#         logger = logging.getLogger('FastDuplicateDetector')
#         logger.setLevel(logging.INFO)
#         if not logger.handlers:
#             handler = logging.StreamHandler()
#             formatter = logging.Formatter(
#                 f'{Fore.CYAN}%(asctime)s{Style.RESET_ALL} - '
#                 f'{Fore.GREEN}%(levelname)s{Style.RESET_ALL} - %(message)s'
#             )
#             handler.setFormatter(formatter)
#             logger.addHandler(handler)
#         return logger

#     def _create_minhash(self, text: str) -> MinHash:
#         """Create MinHash signature for text"""
#         mh = MinHash(num_perm=self.num_perm)
#         for d in self._get_ngrams(text):
#             mh.update(d.encode('utf8'))
#         return mh

#     def _get_ngrams(self, text: str, n: int = 3) -> Set[str]:
#         """Generate character n-grams from text"""
#         text = re.sub(r'\s+', '', str(text).lower())
#         return {''.join(gram) for gram in zip(*[text[i:] for i in range(n)])}

#     def _preprocess_text(self, text: str) -> str:
#         """Basic text preprocessing"""
#         return re.sub(r'\s+', '', str(text).lower())

#     def _create_blocking_key(self, row: pd.Series) -> str:
#         """Create blocking key from specified columns"""
#         if not self.blocking_columns:
#             return ''
#         return ''.join(str(row[col])[0] for col in self.blocking_columns)

#     def _find_exact_duplicates(self, df: pd.DataFrame) -> Tuple[List[DuplicateResult], Set[int]]:
#         """Find exact duplicates using hash-based approach"""
#         hash_dict = defaultdict(list)

#         # Vectorized hash computation
#         df_str = df.astype(str).fillna('')
#         row_hashes = df_str.apply(lambda x: hashlib.md5(''.join(x).encode()).hexdigest(), axis=1)

#         for idx, hash_val in row_hashes.items():
#             hash_dict[hash_val].append(idx)

#         exact_duplicates = []
#         exact_duplicate_indices = set()

#         for indices in hash_dict.values():
#             if len(indices) > 1:
#                 for i, j in combinations(indices, 2):
#                     differences = self._get_row_differences(df.iloc[i], df.iloc[j])
#                     exact_duplicates.append(DuplicateResult(
#                         row_pairs=[(i, j)],
#                         similarity=1.0,
#                         pattern='EXACT',
#                         differences=differences
#                     ))
#                     exact_duplicate_indices.update([i, j])

#         return exact_duplicates, exact_duplicate_indices

#     def _find_near_duplicates_block(self, block_data: Tuple[str, pd.DataFrame]) -> List[DuplicateResult]:
#         """Find near duplicates within a block using MinHash LSH"""
#         block_key, block_df = block_data
#         near_duplicates = []

#         if len(block_df) < 2:
#             return near_duplicates

#         # Create MinHash signatures for each row
#         minhashes = {}
#         lsh = MinHashLSH(threshold=self.near_match_threshold, num_perm=self.num_perm)

#         for idx, row in block_df.iterrows():
#             # Concatenate all fields
#             text = ' '.join(str(val) for val in row)
#             mh = self._create_minhash(text)
#             minhashes[idx] = mh
#             lsh.insert(str(idx), mh)

#         # Find similar pairs
#         for idx1, mh1 in minhashes.items():
#             result = lsh.query(mh1)
#             for r in result:
#                 idx2 = int(r)
#                 if idx1 < idx2:  # Avoid duplicate pairs
#                     similarity = mh1.jaccard(minhashes[idx2])
#                     if similarity >= self.near_match_threshold:
#                         differences = self._get_row_differences(
#                             block_df.loc[idx1],
#                             block_df.loc[idx2]
#                         )
#                         near_duplicates.append(DuplicateResult(
#                             row_pairs=[(idx1, idx2)],
#                             similarity=similarity,
#                             pattern='NEAR_DUPLICATE',
#                             differences=differences
#                         ))

#         return near_duplicates

#     def _get_row_differences(self, row1: pd.Series, row2: pd.Series) -> Dict[str, Tuple[Any, Any]]:
#         """Get differences between two rows for all columns"""
#         return {
#             col: (row1[col], row2[col])
#             for col in row1.index
#             if row1[col] != row2[col]
#         }

#     def find_duplicates(self, df: pd.DataFrame) -> Dict[str, List[DuplicateResult]]:
#         """Find both exact and near duplicates in the dataframe"""
#         start_time = time.time()
#         self.logger.info(f"Starting fast duplicate insight on {len(df):,} rows")

#         # Find exact duplicates
#         exact_duplicates, exact_duplicate_indices = self._find_exact_duplicates(df)

#         # Create blocks for near-duplicate detection
#         if self.blocking_columns:
#             df['_block_key'] = df.apply(self._create_blocking_key, axis=1)
#             blocks = list(df.groupby('_block_key'))
#         else:
#             # If no blocking columns specified, process in chunks
#             chunk_size = max(100, len(df) // (self.n_jobs * 4))
#             blocks = [(str(i), chunk) for i, chunk in
#                       df.groupby(np.arange(len(df)) // chunk_size)]

#         # Process blocks in parallel
#         with ThreadPoolExecutor(max_workers=self.n_jobs) as executor:
#             near_duplicate_lists = list(executor.map(
#                 self._find_near_duplicates_block,
#                 blocks
#             ))

#         # Combine results
#         near_duplicates = [
#             dup for sublist in near_duplicate_lists
#             for dup in sublist
#             if not (dup.row_pairs[0][0] in exact_duplicate_indices or
#                     dup.row_pairs[0][1] in exact_duplicate_indices)
#         ]

#         execution_time = time.time() - start_time
#         self.logger.info(
#             f"Analysis completed in {execution_time:.2f} seconds\n"
#             f"Found {len(exact_duplicates)} exact duplicates and "
#             f"{len(near_duplicates)} near duplicates"
#         )

#         return {
#             'EXACT': exact_duplicates,
#             'NEAR_DUPLICATE': near_duplicates
#         }

#     def generate_report(self, df: pd.DataFrame, results: Dict[str, List[DuplicateResult]],
#                         execution_time: float) -> str:
#         """Generate a detailed, well-formatted report with clear difference highlighting"""
#         exact_matches = len(results.get('EXACT', []))
#         near_matches = len(results.get('NEAR_DUPLICATE', []))
#         total_duplicates = exact_matches + near_matches

#         # Calculate affected rows percentage
#         affected_rows = len(set(
#             idx for pattern in results.values()
#             for result in pattern
#             for pair in result.row_pairs
#             for idx in pair
#         ))
#         affected_percentage = (affected_rows / len(df)) * 100 if len(df) > 0 else 0

#         report_sections = [
#             f"\n{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}",
#             f"{Fore.GREEN}Duplicate Detection Analysis Report{Style.RESET_ALL}",
#             f"{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}\n",
#             f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n",

#             f"{Fore.YELLOW}Summary Statistics:{Style.RESET_ALL}",
#             tabulate([
#                 ['Total Rows Analyzed:', f"{len(df):,}"],
#                 ['Affected Rows:', f"{affected_rows:,} ({affected_percentage:.1f}%)"],
#                 ['Total Duplicates Found:', f"{total_duplicates:,}"],
#                 ['Exact Matches:', f"{exact_matches:,}"],
#                 ['Near Matches:', f"{near_matches:,}"],
#                 ['Execution Time:', f"{execution_time:.2f} seconds"]
#             ], tablefmt='grid'),

#             f"\n{Fore.YELLOW}Duplicate Patterns:{Style.RESET_ALL}"
#         ]

#         # Add sample duplicates with enhanced difference reporting
#         for pattern, duplicates in results.items():
#             if duplicates:
#                 report_sections.extend([
#                     f"\n{Fore.CYAN}{pattern} Duplicates ({len(duplicates)} found):{Style.RESET_ALL}"
#                 ])

#                 # Show up to 3 examples for each pattern
#                 for i, dup in enumerate(duplicates[:3]):
#                     pair = dup.row_pairs[0]
#                     row1_idx, row2_idx = pair

#                     report_sections.extend([
#                         f"\nExample {i + 1}:",
#                         f"Row Indices: ({row1_idx}, {row2_idx})",
#                         f"Similarity: {dup.similarity:.2%}"
#                     ])

#                     if pattern == 'NEAR_DUPLICATE':
#                         if dup.differences:
#                             report_sections.extend([
#                                 f"\n{Fore.YELLOW}Differing Columns:{Style.RESET_ALL}"
#                             ])

#                             # Create a table showing only the differences
#                             diff_rows = []
#                             for col, (val1, val2) in dup.differences.items():
#                                 diff_rows.append([
#                                     col,
#                                     f"Row {row1_idx}: {val1}",
#                                     f"Row {row2_idx}: {val2}"
#                                 ])

#                             report_sections.append(tabulate(
#                                 diff_rows,
#                                 headers=['Column', 'Value 1', 'Value 2'],
#                                 tablefmt='grid'
#                             ))

#                             # Add summary of matching columns
#                             total_cols = len(df.columns)
#                             diff_cols = len(dup.differences)
#                             match_cols = total_cols - diff_cols
#                             report_sections.append(
#                                 f"\nMatching in {match_cols}/{total_cols} columns "
#                                 f"({(match_cols / total_cols) * 100:.1f}% match)"
#                             )
#                     else:  # EXACT match
#                         report_sections.append("(100% match across all columns)")

#                 report_sections.append(f"\n{Fore.CYAN}{'=' * 40}{Style.RESET_ALL}")

#         # Add recommendations based on findings
#         if total_duplicates > 0:
#             recommendations = [
#                 f"\n{Fore.YELLOW}Recommendations:{Style.RESET_ALL}",
#                 "• Review the differing columns in near-duplicates for potential data inconsistencies",
#                 "• Consider standardizing data entry for columns with frequent variations",
#                 f"• Current near-duplicate threshold: {self.near_match_threshold:.0%} "
#                 f"(adjust if needed based on results)",
#             ]
#             report_sections.extend(recommendations)

#         return "\n".join(report_sections)

#     def run_analysis(self, data: pd.DataFrame) -> str:
#         """
#         Run duplicate insight on provided DataFrame and return formatted report

#         Args:
#             data: pandas DataFrame to analyze

#         Returns:
#             str: Formatted report of duplicate insight results
#         """
#         start_time = time.time()
#         self.logger.info(f"Starting duplicate insight on {len(data):,} rows")

#         # Find duplicates
#         results = self.find_duplicates(data)
#         execution_time = time.time() - start_time

#         # Generate and return the report
#         report = self.generate_report(data, results, execution_time)
#         return report

# if __name__ == "__main__":
#     # Test with larger sample data
#     print(f"{Fore.CYAN}Testing with sample dataset...{Style.RESET_ALL}")

#     # Generate larger sample data
#     np.random.seed(42)
#     n_rows = 1000

#     names = ['John Smith', 'Jon Smith', 'John Smyth', 'Jane Doe', 'Janet Doe']
#     emails = ['john@email.com', 'jon@email.com', 'jane@email.com']
#     phones = ['123-456-7890', '123-456-7891', '987-654-3210']

#     sample_data = pd.DataFrame({
#         'name': np.random.choice(names, n_rows),
#         'email': np.random.choice(emails, n_rows),
#         'phone': np.random.choice(phones, n_rows)
#     })

#     # Initialize detector with blocking on first letter of name and email
#     detector = DuplicateDetector(
#         near_match_threshold=0.3,
#         blocking_columns=['name', 'email']
#     )

#     start_time = time.time()
#     results = detector.find_duplicates(sample_data)
#     execution_time = time.time() - start_time

#     print(detector.generate_report(sample_data, results, execution_time))
