# import pandas as pd
# import numpy as np
# import re
# from typing import Dict, Any, List
# from dataclasses import dataclass
# from geopy.geocoders import Nominatim
# from geopy.exc import GeocoderTimedOut
# from collections import Counter


# @dataclass
# class AddressAnalysis:
#     identified_as: str
#     confidence: float
#     sample_values: List[Any]
#     detected_countries: List[str] = None
#     total_rows: int = 0
#     issues: Dict[str, int] = None
#     recommendations: List[str] = None
#     statistics: Dict[str, Any] = None


# class AddressLocationQualityDetector:
#     def __init__(self, data: pd.DataFrame, confidence_threshold: float = 30.0):
#         self.data = data
#         self.confidence_threshold = confidence_threshold
#         self.geolocator = Nominatim(user_agent="address_quality_detector")

#         # Common address patterns
#         self.address_patterns = [
#             r'\d+\s+[\w\s]+(?:street|st|avenue|ave|road|rd|boulevard|blvd|lane|ln|drive|dr|circle|cir|court|ct|way|parkway|pkwy|plaza|plz)',
#             r'p\.?\s*o\.?\s*box\s+\d+',
#             r'(?:apt|suite|ste|unit|#)\s*[\w-]+',
#             r'\d{1,5}\s+\w+\s+(?:street|st|ave|rd|blvd|ln|dr|cir|ct)',
#         ]

#         # Column name patterns for address-related fields
#         self.column_patterns = [
#             r'(?i)(^|_)(address|location|street|residence|premises|building)($|_)',
#             r'(?i)(^|_)(city|town|municipality|district|region|state|province|country)($|_)',
#             r'(?i)(^|_)(postal|zip|pincode|postcode)($|_)',
#             r'(?i)(^|_)(landmark|area|locality|neighborhood|neighbourhood)($|_)'
#         ]

#         # Non-address patterns
#         self.non_address_patterns = [
#             r'(?i)(^|_)(email|phone|url|website|link|ip)($|_)',
#             r'(?i)(^|_)(price|amount|cost|payment|salary|fee)($|_)',
#             r'(?i)(^|_)(date|time|duration|age|year|month)($|_)',
#             r'(?i)(^|_)(id|identifier|key|code|reference)($|_)',
#             r'(?i)(^|_)(status|type|category|class|group)($|_)'
#         ]

#         # Common postal code formats by country
#         self.postal_code_patterns = {
#             'US': r'^\d{5}(-\d{4})?$',
#             'UK': r'^[A-Z]{1,2}\d[A-Z\d]? ?\d[A-Z]{2}$',
#             'CA': r'^[A-Z]\d[A-Z] ?\d[A-Z]\d$',
#             'AU': r'^\d{4}$',
#             'IN': r'^\d{6}$',
#             'DE': r'^\d{5}$',
#             'FR': r'^\d{5}$',
#             'JP': r'^\d{3}-?\d{4}$'
#         }

#     def _calculate_confidence(self, column: str, values: pd.Series) -> float:
#         """Calculate confidence score for address identification."""
#         column_lower = column.lower()

#         # Early return for non-address patterns
#         if any(re.search(pattern, column_lower) for pattern in self.non_address_patterns):
#             return 0

#         score = 0
#         weights = {
#             'column_name': 30,
#             'value_format': 30,
#             'geocoding': 20,
#             'statistical': 20
#         }

#         # Column name analysis
#         if any(re.search(pattern, column_lower) for pattern in self.column_patterns):
#             score += weights['column_name']

#         # Value format analysis
#         valid_values = sum(self._is_address_format(val) for val in values if pd.notna(val))
#         if len(values) > 0:
#             format_score = (valid_values / len(values)) * weights['value_format']
#             score += format_score

#         # Geocoding sample check
#         sample_size = min(5, len(values))
#         if sample_size > 0:
#             sample_values = values.dropna().sample(n=sample_size, random_state=42)
#             geocoded = sum(self._try_geocode(str(val)) for val in sample_values)
#             geocoding_score = (geocoded / sample_size) * weights['geocoding']
#             score += geocoding_score

#         # Statistical analysis
#         stats = self._calculate_statistics(values)
#         if stats:
#             avg_word_count = stats.get("avg_word_count", 0)
#             if 3 <= avg_word_count <= 15:  # Typical address word count range
#                 score += weights['statistical']

#         return min(max(score, 0), 100)

#     def _is_address_format(self, value: Any) -> bool:
#         """Check if value matches common address formats."""
#         if pd.isna(value):
#             return False

#         value_str = str(value).lower().strip()

#         # Check common address patterns
#         for pattern in self.address_patterns:
#             if re.search(pattern, value_str, re.IGNORECASE):
#                 return True

#         # Check for numeric start (common in addresses)
#         if re.match(r'^\d+\s+', value_str):
#             return True

#         # Check for PO Box format
#         if re.search(r'p\.?o\.?\s*box', value_str, re.IGNORECASE):
#             return True

#         # Check for apartment/suite indicators
#         if re.search(r'(?:apt|suite|ste|unit|#)\s*[\w-]+', value_str, re.IGNORECASE):
#             return True

#         return False

#     def _try_geocode(self, address: str) -> bool:
#         """Attempt to geocode an address."""
#         try:
#             location = self.geolocator.geocode(address, timeout=5)
#             return location is not None
#         except (GeocoderTimedOut, Exception):
#             return False

#     def _calculate_statistics(self, values: pd.Series) -> Dict[str, Any]:
#         """Calculate statistical measures for the column."""
#         stats = {}

#         # Word count statistics
#         word_counts = [len(str(v).split()) for v in values if pd.notna(v)]
#         if word_counts:
#             stats["avg_word_count"] = np.mean(word_counts)
#             stats["min_word_count"] = min(word_counts)
#             stats["max_word_count"] = max(word_counts)

#         # Character length statistics
#         char_lengths = [len(str(v)) for v in values if pd.notna(v)]
#         if char_lengths:
#             stats["avg_length"] = np.mean(char_lengths)
#             stats["min_length"] = min(char_lengths)
#             stats["max_length"] = max(char_lengths)

#         # Detect most common country format
#         countries = []
#         for value in values:
#             if pd.notna(value):
#                 for country, pattern in self.postal_code_patterns.items():
#                     if re.search(pattern, str(value)):
#                         countries.append(country)
#         if countries:
#             stats["common_country_format"] = Counter(countries).most_common(1)[0][0]

#         return stats

#     def _identify_issues(self, values: pd.Series) -> Dict[str, int]:
#         """Identify issues in the address column."""
#         issues = {
#             "missing_values": 0,
#             "invalid_format": 0,
#             "incomplete_address": 0,
#             "non_geocodable": 0,
#             "inconsistent_format": 0,
#             "unusual_length": 0,
#             "duplicate_addresses": 0,
#             "invalid_characters": 0
#         }

#         stats = self._calculate_statistics(values)
#         avg_length = stats.get("avg_length", 0)
#         duplicates = values.duplicated()

#         for value in values:
#             if pd.isna(value):
#                 issues["missing_values"] += 1
#                 continue

#             str_value = str(value)

#             # Check for invalid characters
#             if re.search(r'[^a-zA-Z0-9\s,.\-#/]', str_value):
#                 issues["invalid_characters"] += 1

#             # Check for incomplete addresses
#             if len(str_value.split()) < 3:
#                 issues["incomplete_address"] += 1

#             # Check for unusual lengths
#             if len(str_value) < 10 or len(str_value) > 200:
#                 issues["unusual_length"] += 1

#             # Check for invalid format
#             if not self._is_address_format(str_value):
#                 issues["invalid_format"] += 1

#             # Check if address can be geocoded
#             if not self._try_geocode(str_value):
#                 issues["non_geocodable"] += 1

#         # Count duplicates
#         issues["duplicate_addresses"] = duplicates.sum()

#         # Check for inconsistent formats
#         format_patterns = [
#             r'^\d+\s+',  # Starts with number
#             r'p\.?o\.?\s*box',  # PO Box format
#             r'(?:apt|suite|ste|unit|#)'  # Apartment/suite format
#         ]
#         formats_used = set()
#         for value in values:
#             if pd.notna(value):
#                 for pattern in format_patterns:
#                     if re.search(pattern, str(value), re.IGNORECASE):
#                         formats_used.add(pattern)
#         if len(formats_used) > 1:
#             issues["inconsistent_format"] = len(values)

#         return {k: v for k, v in issues.items() if v > 0}

#     def _generate_recommendations(self, issues: Dict[str, int], total_rows: int) -> List[str]:
#         """Generate recommendations based on identified issues."""
#         recommendations = []

#         issue_thresholds = {
#             "missing_values": 0.05,
#             "invalid_format": 0.02,
#             "incomplete_address": 0.05,
#             "non_geocodable": 0.10,
#             "inconsistent_format": 0.10,
#             "unusual_length": 0.05,
#             "duplicate_addresses": 0.02,
#             "invalid_characters": 0.01
#         }

#         recommendations_map = {
#             "missing_values": "Handle missing addresses through data collection or removal.",
#             "invalid_format": "Standardize address format according to postal service guidelines.",
#             "incomplete_address": "Collect complete address information including street number, name, and postal code.",
#             "non_geocodable": "Verify and correct addresses that cannot be geocoded.",
#             "inconsistent_format": "Implement consistent address formatting across all entries.",
#             "unusual_length": "Review unusually short or long addresses for potential errors.",
#             "duplicate_addresses": "Investigate and resolve duplicate address entries.",
#             "invalid_characters": "Remove or replace invalid characters in addresses."
#         }

#         for issue, count in issues.items():
#             if count / total_rows > issue_thresholds[issue]:
#                 recommendations.append(recommendations_map[issue])

#         return recommendations

#     def analyze_column(self, column: str) -> AddressAnalysis:
#         """Analyze a single column for address quality."""
#         values = self.data[column].dropna()
#         confidence = self._calculate_confidence(column, values)

#         is_address = confidence >= self.confidence_threshold
#         detected_countries = set()

#         if is_address:
#             stats = self._calculate_statistics(values)
#             if "common_country_format" in stats:
#                 detected_countries.add(stats["common_country_format"])

#         issues = self._identify_issues(values)
#         recommendations = self._generate_recommendations(issues, len(values))
#         statistics = self._calculate_statistics(values)

#         return AddressAnalysis(
#             identified_as="ADDRESS" if is_address else "NON_ADDRESS",
#             confidence=confidence,
#             sample_values=values.head(5).tolist(),
#             detected_countries=list(detected_countries) if is_address else None,
#             total_rows=len(values),
#             issues=issues,
#             recommendations=recommendations,
#             statistics=statistics
#         )

#     def run(self) -> Dict[str, AddressAnalysis]:
#         """Run analysis on all columns."""
#         all_results = {column: self.analyze_column(column) for column in self.data.columns}
#         return {col: analysis for col, analysis in all_results.items()
#                 if analysis.identified_as == "ADDRESS"}


# def format_time(seconds):
#     """Convert seconds into a human-readable format"""
#     if seconds < 60:
#         return f"{seconds:.2f} seconds"
#     elif seconds < 3600:
#         minutes = seconds // 60
#         remaining_seconds = seconds % 60
#         return f"{int(minutes)} minutes and {remaining_seconds:.2f} seconds"
#     else:
#         hours = seconds // 3600
#         remaining_minutes = (seconds % 3600) // 60
#         remaining_seconds = seconds % 60
#         return f"{int(hours)} hours, {int(remaining_minutes)} minutes and {remaining_seconds:.2f} seconds"

# # Example usage
# if __name__ == "__main__":
#     # Example data
#     data = {
#         "shipping_address": [
#             "123 Main St, Suite 100, Boston, MA 02108",
#             "456 Park Ave, New York, NY 10022",
#             "P.O. Box 789, Chicago, IL 60601",
#             "987 Market St, San Francisco, CA 94103",
#             "321 Oak Rd, Apt 5B, Miami, FL 33101"
#         ],
#         "billing_address": [
#             "789 Broadway, New York, NY 10003",
#             "654 Pine St, Seattle, WA 98101",
#             "321 Elm St, Unit 2C, Boston, MA 02115",
#             "147 Main St, Los Angeles, CA 90012",
#             "852 First Ave, Chicago, IL 60611"
#         ],
#         "email": [
#             "john@email.com",
#             "jane@email.com",
#             "bob@email.com",
#             "alice@email.com",
#             "sam@email.com"
#         ]
#     }

#     file_path = r"C:\Users\admin\Downloads\South_Superstore_V1.csv"
#     df = pd.read_csv(file_path, encoding='windows-1252')
#     # df = pd.DataFrame(data)
#     detector = AddressLocationQualityDetector(df)
#     report = detector.run()

#     # Display detailed results for address columns only
#     for column, analysis in report.items():
#         print(f"\nColumn: {column}")
#         print(f"Classification: {analysis.identified_as}")
#         print(f"Confidence: {analysis.confidence:.2f}%")
#         print(f"Sample Values: {analysis.sample_values}")

#         if analysis.detected_countries:
#             print(f"Detected Countries: {analysis.detected_countries}")

#         if analysis.issues:
#             print("\nIssues Detected:")
#             for issue, count in analysis.issues.items():
#                 print(f"- {issue}: {count} occurrences")

#         if analysis.recommendations:
#             print("\nRecommendations:")
#             for rec in analysis.recommendations:
#                 print(f"- {rec}")

#         if analysis.statistics:
#             print("\nStatistics:")
#             for stat, value in analysis.statistics.items():
#                 print(f"- {stat}: {value}")

#         print("-" * 50)