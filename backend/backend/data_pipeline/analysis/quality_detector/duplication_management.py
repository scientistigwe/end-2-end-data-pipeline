import pandas as pd
import re
from typing import List, Tuple, Optional
import pandas as pd
import numpy as np
import re
from typing import Any, List, Tuple, Set
from rapidfuzz import fuzz
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer
import datetime


class ComprehensiveDuplicateDetector:
    def __init__(self, data: pd.DataFrame):
        """
        Initialize the duplicate detector with a dataset.
        Args:
            data: A pandas DataFrame containing the data to analyze.
        """
        self.data = data

    @staticmethod
    def _normalize_text(value: Optional[str]) -> str:
        """
        Normalize text by removing extra spaces, converting to lowercase, and handling NaNs.
        Args:
            value: Input string or None.
        Returns:
            Normalized string.
        """
        if not isinstance(value, str):
            return ""
        return re.sub(r"\s+", " ", value.strip().lower())

    def find_exact_duplicates(self) -> List[Tuple[int, int]]:
        """Find exact duplicates in the dataset."""
        duplicates = []
        for col in self.data.columns:
            unique_values = {}
            for idx, value in self.data[col].iteritems():
                if value in unique_values:
                    duplicates.append((unique_values[value], idx))
                else:
                    unique_values[value] = idx
        return duplicates

    def find_partial_duplicates(self) -> List[Tuple[int, int]]:
        """Find duplicates based on partial matches."""
        duplicates = []
        for col in self.data.columns:
            for i in range(len(self.data)):
                for j in range(i + 1, len(self.data)):
                    if isinstance(self.data.iloc[i, self.data.columns.get_loc(col)], str) and isinstance(
                            self.data.iloc[j, self.data.columns.get_loc(col)], str
                    ):
                        if self.data.iloc[i, self.data.columns.get_loc(col)] in self.data.iloc[
                            j, self.data.columns.get_loc(col)
                        ] or self.data.iloc[j, self.data.columns.get_loc(col)] in self.data.iloc[
                            i, self.data.columns.get_loc(col)
                        ]:
                            duplicates.append((i, j))
        return duplicates

    def find_fuzzy_duplicates(self, column: str, threshold: int = 85) -> List[Tuple[int, int]]:
        """
        Find fuzzy matches in a specific column using simple text comparison.
        Args:
            column: The column to check for duplicates.
            threshold: Minimum similarity percentage (0-100) to consider as a match.
        Returns:
            List of tuple pairs (row_index_1, row_index_2) for fuzzy duplicates.
        """
        from rapidfuzz import fuzz

        duplicates = []
        column_data = self.data[column].fillna("").astype(str)
        for i in range(len(column_data)):
            for j in range(i + 1, len(column_data)):
                if fuzz.ratio(column_data[i], column_data[j]) >= threshold:
                    duplicates.append((i, j))
        return duplicates

    def find_whitespace_sensitive_duplicates(self, column: str) -> List[Tuple[int, int]]:
        """
        Detect duplicates that differ only in leading/trailing whitespaces in a column.
        Args:
            column: The column to check.
        Returns:
            List of tuple pairs (row_index_1, row_index_2) for whitespace-sensitive duplicates.
        """
        duplicates = []
        column_data = self.data[column].fillna("").astype(str)
        for i in range(len(column_data)):
            for j in range(i + 1, len(column_data)):
                if column_data[i].strip() == column_data[j].strip() and column_data[i] != column_data[j]:
                    duplicates.append((i, j))
        return duplicates

    def find_cross_field_duplicates(self, column1: str, column2: str) -> List[Tuple[int, int]]:
        """
        Find rows where values in two columns are identical across rows.
        Args:
            column1: First column to compare.
            column2: Second column to compare.
        Returns:
            List of tuple pairs (row_index_1, row_index_2) for cross-field duplicates.
        """
        duplicates = []
        for i in range(len(self.data)):
            for j in range(i + 1, len(self.data)):
                if self.data.iloc[i][column1] == self.data.iloc[j][column2]:
                    duplicates.append((i, j))
        return duplicates

    def run_detection(self, methods: List[str], columns: Optional[List[str]] = None) -> List[Tuple[int, int, str]]:
        """
        Execute duplicate detection across specified methods and columns.
        Args:
            methods: List of detection methods to use.
                     Available: ["exact", "partial", "fuzzy", "whitespace_sensitive", "cross_field"]
            columns: Specific columns to check for partial or cross-field duplicates (if applicable).
        Returns:
            List of detected duplicate pairs with the method used.
        """
        results = []

        if "exact" in methods:
            results.extend([(i, j, "exact") for i, j in self.find_exact_duplicates()])

        if "partial" in methods and columns:
            results.extend([(i, j, "partial") for i, j in self.find_partial_duplicates(columns)])

        if "fuzzy" in methods and columns:
            for col in columns:
                results.extend([(i, j, f"fuzzy ({col})") for i, j in self.find_fuzzy_duplicates(col)])

        if "whitespace_sensitive" in methods and columns:
            for col in columns:
                results.extend([(i, j, f"whitespace_sensitive ({col})") for i, j in self.find_whitespace_sensitive_duplicates(col)])

        if "cross_field" in methods and len(columns) == 2:
            results.extend([(i, j, "cross_field") for i, j in self.find_cross_field_duplicates(columns[0], columns[1])])

        return results


class EnhancedFuzzyDuplicateDetector:
    def __init__(self, data: pd.DataFrame, similarity_threshold: float = 0.85, model_name: str = "all-MiniLM-L6-v2"):
        """
        Enhanced duplicate detector leveraging modern NLP and clustering techniques.

        Args:
            data: Input dataframe to process.
            similarity_threshold: Threshold for identifying duplicates (0-1 range).
            model_name: SentenceTransformer model for embeddings.
        """
        self.data = data
        self.similarity_threshold = similarity_threshold
        self.data = data
        self.similarity_thresholds = similarity_thresholds or {
            'approximate': 0.85,
            'contextual': 0.75,
            'semantic': 0.80
        }
        self.domain_rules = domain_rules or {}
        self.duplicate_prone_patterns = [r"id", r"name", r"email", r"phone"]
        self.unique_value_patterns = [r"serial", r"unique"]

    def _normalize_text(self, text: Any) -> str:
        """Normalize text for duplicate detection."""
        if pd.isna(text):
            return ""
        return re.sub(r"\s+", " ", str(text).strip().lower())

    def _calculate_text_similarity(self, text_series: pd.Series) -> pd.DataFrame:
        """Compute pairwise text similarity using TF-IDF and cosine similarity."""
        normalized_texts = text_series.apply(self._normalize_text).tolist()
        tfidf = TfidfVectorizer().fit_transform(normalized_texts)
        similarity_matrix = cosine_similarity(tfidf)
        return pd.DataFrame(similarity_matrix, index=text_series.index, columns=text_series.index)

    def _semantic_similarity(self, text_series: pd.Series) -> pd.DataFrame:
        """Calculate semantic similarity using sentence embeddings."""
        normalized_texts = text_series.apply(self._normalize_text).tolist()
        embeddings = self.model.encode(normalized_texts)
        similarity_matrix = cosine_similarity(embeddings)
        return pd.DataFrame(similarity_matrix, index=text_series.index, columns=text_series.index)

    def _detect_clusters(self, similarity_matrix: pd.DataFrame) -> List[Set[int]]:
        """Cluster records based on similarity matrix using DBSCAN."""
        clustering = DBSCAN(eps=1 - self.similarity_threshold, min_samples=2, metric="precomputed")
        labels = clustering.fit_predict(1 - similarity_matrix.values)
        clusters = []
        for label in set(labels):
            if label == -1:  # Exclude noise points
                continue
            cluster_indices = similarity_matrix.index[labels == label].tolist()
            clusters.append(set(cluster_indices))
        return clusters

    def find_duplicates(self, text_column: str, method: str = "tfidf") -> List[Tuple[int, int]]:
        """
        Find duplicates in the specified column using the chosen similarity method.

        Args:
            text_column: The name of the column to analyze.
            method: Similarity method, one of ['tfidf', 'semantic'].

        Returns:
            List of tuples representing duplicate record indices.
        """
        if method not in ["tfidf", "semantic"]:
            raise ValueError("Unsupported method. Choose between 'tfidf' and 'semantic'.")

        text_series = self.data[text_column]
        if method == "tfidf":
            similarity_matrix = self._calculate_text_similarity(text_series)
        else:
            similarity_matrix = self._semantic_similarity(text_series)

        clusters = self._detect_clusters(similarity_matrix)
        duplicates = [(i, j) for cluster in clusters for i in cluster for j in cluster if i < j]
        return duplicates

    def run_detection(self, methods: List[str] = ["tfidf", "semantic"]) -> List[Tuple[int, int, str]]:
        """
        Run duplicate detection for all text columns using specified methods.

        Args:
            methods: List of similarity methods to use.

        Returns:
            List of detected duplicate pairs with methods used.
        """
        results = []
        text_columns = self.data.select_dtypes(include=["object"]).columns

        for col in text_columns:
            for method in methods:
                duplicates = self.find_duplicates(text_column=col, method=method)
                results.extend([(i, j, f"Fuzzy match in '{col}' ({method})") for i, j in duplicates])

        return results

    def _calculate_confidence(self, duplicates_info: Dict[str, List[Tuple]], column: Optional[str] = None) -> float:
        """Calculate a confidence score for the duplicate detection."""
        score = 0
        weights = {'column_name': 30, 'duplicate_types': 40, 'value_distribution': 30}

        if column:
            column_lower = column.lower()
            if any(re.search(pattern, column_lower) for pattern in self.duplicate_prone_patterns):
                score += weights['column_name']
            if any(re.search(pattern, column_lower) for pattern in self.unique_value_patterns):
                score -= weights['column_name']

        total_duplicates = sum(len(dupes) for dupes in duplicates_info.values())
        if total_duplicates > 0:
            types_score = min(len(duplicates_info) * 10, weights['duplicate_types'])
            score += types_score

        if column:
            unique_ratio = len(self.data[column].unique()) / len(self.data[column])
            distribution_score = (1 - unique_ratio) * weights['value_distribution']
            score += distribution_score

        return min(max(score, 0), 100)

    def _calculate_text_similarity(self, text_series: pd.Series) -> pd.DataFrame:
        """Compute similarity using TF-IDF."""
        normalized_texts = text_series.apply(self._normalize_text).tolist()
        tfidf = TfidfVectorizer().fit_transform(normalized_texts)
        similarity_matrix = cosine_similarity(tfidf)
        return pd.DataFrame(similarity_matrix, index=text_series.index, columns=text_series.index)

    def _semantic_similarity(self, text_series: pd.Series) -> pd.DataFrame:
        """Calculate semantic similarity using embeddings."""
        if not self.use_ml:
            raise ValueError("ML-based similarity is disabled.")
        normalized_texts = text_series.apply(self._normalize_text).tolist()
        embeddings = self.model.encode(normalized_texts)
        similarity_matrix = cosine_similarity(embeddings)
        return pd.DataFrame(similarity_matrix, index=text_series.index, columns=text_series.index)

    def _generate_recommendations(self, duplicates_info: Dict[str, List[Tuple]], statistics: Dict[str, float],
                                  impact_assessment: Dict[str, float]) -> List[str]:
        """Generate tailored recommendations for duplicate mitigation."""
        recommendations = []

        if statistics["total_duplicates"] > 0:
            recommendations.append("Implement automated duplicate detection in the data pipeline.")

        if duplicates_info.get("exact"):
            recommendations.append("Use pandas `drop_duplicates()` to handle exact duplicates.")

        if duplicates_info.get("approximate"):
            recommendations.append("Implement fuzzy matching with a configurable similarity threshold.")

        if impact_assessment["data_quality_score"] < 70:
            recommendations.append("Prioritize duplicate resolution to improve data quality.")

        return recommendations

    def get_duplicate_summary(self, analysis_results: Dict[str, Dict[str, Any]]) -> pd.DataFrame:
        """Generate a summary DataFrame for the analysis."""
        summary_data = []

        for name, result in analysis_results.items():
            summary_data.append({
                "Name": name,
                "Confidence": f"{result['confidence']:.2f}%",
                "Total Duplicates": result["statistics"]["total_duplicates"],
                "Types Found": len(result["duplicates"]),
                "Quality Impact": f"{result['impact_assessment']['data_quality_score']:.2f}%",
                "Affected Rows": f"{result['impact_assessment']['affected_rows_percentage']:.2f}%"
            })

        return pd.DataFrame(summary_data)

    def export_detailed_report(self, analysis_results: Dict[str, Dict[str, Any]]) -> str:
        """Generate a markdown report with analysis details."""
        report = ["# Duplicate Analysis Report"]
        report.append(f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

        for name, result in analysis_results.items():
            report.append(f"## {name}")
            report.append(f"- Confidence: {result['confidence']:.2f}%")
            report.append(f"- Total Duplicates: {result['statistics']['total_duplicates']}")
            for recommendation in result['recommendations']:
                report.append(f"- {recommendation}")

        return "\n".join(report)

    def run_analysis(self) -> Dict[str, Dict[str, Any]]:
        """Run the full analysis."""
        analysis_results = {}
        for col in self.data.select_dtypes(include=["object"]):
            duplicates = {"exact": [], "approximate": []}  # Example placeholders
            statistics = {"total_duplicates": len(duplicates["exact"])}
            impact_assessment = {"data_quality_score": 85.0, "affected_rows_percentage": 10.0}

            confidence = self._calculate_confidence(duplicates, column=col)
            recommendations = self._generate_recommendations(duplicates, statistics, impact_assessment)

            analysis_results[col] = {
                "duplicates": duplicates,
                "statistics": statistics,
                "impact_assessment": impact_assessment,
                "confidence": confidence,
                "recommendations": recommendations
            }

        return analysis_results


class ComprehensiveDuplicateDetector:
    def __init__(self, data: pd.DataFrame):
        self.data = data

    def find_exact_duplicates(self) -> List[Tuple[int, int]]:
        return [(i, j) for i in range(len(self.data)) for j in range(i+1, len(self.data)) if all(self.data.iloc[i] == self.data.iloc[j])]

    def find_partial_duplicates(self) -> List[Tuple[int, int]]:
        return [(i, j) for i in range(len(self.data))
                for j in range(i+1, len(self.data))
                if self.data.iloc[i].equals(self.data.iloc[j])]

    def find_case_sensitive_duplicates(self) -> List[Tuple[int, int]]:
        return [(i, j) for i in range(len(self.data))
                for j in range(i+1, len(self.data))
                if self.data.iloc[i].astype(str).str.lower() == self.data.iloc[j].astype(str).lower()]

    def find_whitespace_duplicates(self) -> List[Tuple[int, int]]:
        return [(i, j) for i in range(len(self.data))
                for j in range(i+1, len(self.data))
                if self.data.iloc[i].astype(str).str.strip().lower() == self.data.iloc[j].astype(str).strip().lower()]

    def find_fuzzy_duplicates(self, threshold: float = 0.85) -> List[Tuple[int, int]]:
        duplicates = []
        for col in self.data.columns:
            for i in range(len(self.data)):
                for j in range(i+1, len(self.data)):
                    if isinstance(self.data.iloc[i, self.data.columns.get_loc(col)], str) and isinstance(self.data.iloc[j, self.data.columns.get_loc(col)], str):
                        similarity = fuzz.ratio(self.data.iloc[i, self.data.columns.get_loc(col)].astype(str), self.data.iloc[j, self.data.columns.get_loc(col)].astype(str))
                        if similarity >= threshold:
                            duplicates.append((i, j))
        return duplicates

    def find_different_representations(self) -> List[Tuple[int, int]]:
        return [(i, j) for i in range(len(self.data))
                 for j in range(i+1, len(self.data))
                 if set(self.data.iloc[i]) != set(self.data.iloc[j])]

    def find_temporal_duplicates(self, time_column: str) -> List[Tuple[int, int]]:
        return [(i, j) for i in range(len(self.data))
                 for j in range(i+1, len(self.data))
                 if self.data.iloc[i, self.data.columns.get_loc(time_column)] == self.data.iloc[j, self.data.columns.get_loc(time_column)]]

    def find_aggregated_duplicates(self) -> List[Tuple[int, int]]:
        return [(i, j) for i in range(len(self.data))
                 for j in range(i+1, len(self.data))
                 if sum(self.data.iloc[i]) == sum(self.data.iloc[j])]

    def find_contextual_duplicates(self, column1: str, column2: str) -> List[Tuple[int, int]]:
        return [(i, j) for i in range(len(self.data))
                 for j in range(i+1, len(self.data))
                 if self.data.iloc[i][column1] == self.data.iloc[j][column2]]

    def find_derived_calculated_duplicates(self) -> List[Tuple[int, int]]:
        return [(i, j) for i in range(len(self.data))
                 for j in range(i+1, len(self.data))
                 if np.isclose(self.data.iloc[i], self.data.iloc[j]).any()]

    def find_multi_field_duplicates(self, columns: List[str]) -> List[Tuple[int, int]]:
        return [(i, j) for i in range(len(self.data))
                 for j in range(i+1, len(self.data))
                 if set(zip(*[self.data.iloc[i][col] for col in columns])) == set(zip(*[self.data.iloc[j][col] for col in columns]))]

    def find_cross_column_duplicates(self) -> List[Tuple[int, int]]:
        return [(i, j) for i in range(len(self.data))
                 for j in range(i+1, len(self.data))
                 if set(self.data.iloc[i].tolist()) & set(self.data.iloc[j].tolist())]

    def find_hierarchical_duplicates(self, group_column: str) -> List[Tuple[int, int]]:
        return [(i, j) for i in range(len(self.data))
                 for j in range(i+1, len(self.data))
                 if self.data.iloc[i][group_column] == self.data.iloc[j][group_column]]

    def run_detection(self, methods: List[str]) -> List[Tuple[int, int, str]]:
        results = []
        for method in methods:
            if method == 'exact':
                results.extend(self.find_exact_duplicates())
            elif method == 'partial':
                results.extend(self.find_partial_duplicates())
            elif method == 'case_sensitive':
                results.extend(self.find_case_sensitive_duplicates())
            elif method == 'whitespace':
                results.extend(self.find_whitespace_duplicates())
            elif method == 'fuzzy':
                results.extend(self.find_fuzzy_duplicates())
            elif method == 'different_representations':
                results.extend(self.find_different_representations())
            elif method == 'temporal':
                results.extend(self.find_temporal_duplicates('date'))
            elif method == 'aggregated':
                results.extend(self.find_aggregated_duplicates())
            elif method == 'contextual':
                results.extend(self.find_contextual_duplicates('location', 'name'))
            elif method == 'derived_calculated':
                results.extend(self.find_derived_calculated_duplicates())
            elif method == 'multi_field':
                results.extend(self.find_multi_field_duplicates(['name', 'email']))
            elif method == 'cross_column':
                results.extend(self.find_cross_column_duplicates())
            elif method == 'hierarchical':
                results.extend(self.find_hierarchical_duplicates('category'))

        return results

# Example usage
data = pd.DataFrame({
    'ID': [1, 2, 3, 4],
    'Name': ['Alice', 'Bob', 'Charlie', 'David'],
    'Age': [25, 30, 35, 40],
    'City': ['NY', 'LA', 'NY', 'CHI'],
    'Email': ['alice@example.com', 'bob@example.com', 'charlie@example.com', 'david@example.com'],
    'Date': ['2023-01-01', '2023-01-02', '2023-01-03', '2023-01-04']
})

# Example dataset
data = pd.DataFrame({
    "Name": ["Alice", "Bob", "alice ", "BOB", "Charlie"],
    "Email": ["alice@example.com", "bob@example.com", "alice@example.com", "bob@example.com", "charlie@example.com"],
    "Age": [25, 30, 25, 30, 35]
})

detector = ComprehensiveDuplicateDetector(data)

methods = [
    'exact',
    'partial',
    'case_sensitive',
    'whitespace',
    'fuzzy',
    'different_representations',
    'temporal',
    'aggregated',
    'contextual',
    'derived_calculated',
    'multi_field',
    'cross_column',
    'hierarchical'
]

results = detector.run_detection(methods)

print("Detected duplicates:")
for result in results:
    print(f"Row {result[0]} and Row {result[1]}")
