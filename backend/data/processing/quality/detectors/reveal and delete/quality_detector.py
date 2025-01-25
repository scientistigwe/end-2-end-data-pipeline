# import calendar
# from ipaddress import ip_network, ip_address, IPv4Address, IPv6Address
# from typing import Dict, List, Any, Tuple, Optional, Set, Union
# from dataclasses import dataclass
# from enum import Enum
# import logging
# from collections import defaultdict, Counter
# import phonenumbers
# from email_validator import validate_email, EmailNotValidError
# import re
# import pandas as pd
# from datetime import datetime
# import time
# from dateutil import parser
#
#
# # Configure logging
# logging.basicConfig(
#     level=logging.INFO,
#     format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
# )
# logger = logging.getLogger(__name__)
#
#
# class DataTypes(Enum):
#     COORDINATES = "coordinates"
#     SSN = "ssn"
#     CREDIT_CARD = "credit_card"
#     IP_ADDRESS = "ip_address"
#     POSTAL_CODE = "postal_code"
#     CURRENCY_CODE = "currency_code"
#     DATE = "date"
#     PHONE = "phone"
#     EMAIL = "email"
#     NUMERIC = "numeric"
#     TEXT = "text"
#     DESCRIPTIVE_TEXT = "descriptive_text"
#     CATEGORICAL = "categorical"
#     UNKNOWN = "unknown"
#
#
# @dataclass
# class DetectionResult:
#     """Stores detection results for each value pattern insight"""
#     column_type: str
#     match_percentage: float
#     consistent_samples: List[str]
#     inconsistent_samples: List[str]
#     inconsistency_percentage: float
#     total_rows: int
#     row_counts: Dict[str, int]
#
#
# import re
# import calendar
# from datetime import datetime
# from typing import Tuple
# import pandas as pd
# from dateutil import parser
# from dataclasses import dataclass
# from collections import defaultdict
#
# @dataclass
# class DetectionResult:
#     column_type: str
#     match_percentage: float
#     consistent_samples: list
#     inconsistent_samples: list
#     inconsistency_percentage: float
#     total_rows: int
#     row_counts: dict
#
#
# class PatternDetector:
#     def __init__(self, name: str, pattern_type: str, confidence_threshold: float = 99.0):
#         self.name = name
#         self.pattern_type = pattern_type
#         self.confidence_threshold = confidence_threshold
#
#     def detect(self, value: str) -> tuple[bool, str]:
#         raise NotImplementedError("Subclasses must implement detect() method")
#
#     def analyze_column(self, series: pd.Series) -> DetectionResult:
#         total_rows = len(series.dropna())
#         if total_rows == 0:
#             return DetectionResult(
#                 column_type=self.pattern_type,
#                 match_percentage=0,
#                 consistent_samples=[],
#                 inconsistent_samples=[],
#                 inconsistency_percentage=0,
#                 total_rows=0,
#                 row_counts={'empty': len(series)}
#             )
#
#         matches = []
#         reasons = defaultdict(list)
#         consistent_samples = []
#         inconsistent_samples = []
#
#         for value in series.dropna():
#             str_value = str(value).strip()
#             is_match, reason = self.detect(str_value)
#             matches.append(is_match)
#
#             if is_match:
#                 if len(consistent_samples) < 3 and str_value not in consistent_samples:
#                     consistent_samples.append(str_value)
#             else:
#                 if len(inconsistent_samples) < 3 and str_value not in inconsistent_samples:
#                     inconsistent_samples.append(str_value)
#                 reasons[reason].append(str_value)
#
#         match_count = sum(matches)
#         match_percentage = (match_count / total_rows) * 100
#         inconsistency_percentage = 100 - match_percentage
#
#         row_counts = {
#             'total': total_rows,
#             'matches': match_count,
#             'non_matches': total_rows - match_count,
#             **{f"reason_{reason}": len(values) for reason, values in reasons.items()},
#         }
#
#         return DetectionResult(
#             column_type=self.pattern_type,
#             match_percentage=match_percentage,
#             consistent_samples=consistent_samples,
#             inconsistent_samples=inconsistent_samples,
#             inconsistency_percentage=inconsistency_percentage,
#             total_rows=total_rows,
#             row_counts=row_counts
#         )
#
#
# class PatternResolver:
#     @staticmethod
#     def resolve_multi_match(results: dict[str, list[DetectionResult]]) -> dict[str, DetectionResult]:
#         """
#         Resolve conflicts between pattern detectors with high specificity.
#         """
#         resolved_results = {}
#         for column, column_results in results.items():
#             sorted_results = sorted(
#                 column_results,
#                 key=lambda result: result.match_percentage,
#                 reverse=True
#             )
#
#             top_result = sorted_results[0]
#             if top_result.match_percentage >= 99.0:
#                 resolved_results[column] = top_result
#             else:
#                 resolved_results[column] = DetectionResult(
#                     column_type="ambiguous",
#                     match_percentage=0,
#                     consistent_samples=[],
#                     inconsistent_samples=[],
#                     inconsistency_percentage=100,
#                     total_rows=top_result.total_rows,
#                     row_counts={"ambiguous_detectors": [r.column_type for r in sorted_results]}
#                 )
#
#         return resolved_results
#
#
# class DateDetector(PatternDetector):
#     def __init__(self):
#         super().__init__("Date", "date", confidence_threshold=99.0)
#         self.strict_formats = [
#             ('%Y-%m-%d', 'iso'),
#             ('%Y/%m/%d', 'iso_slash'),
#             ('%d-%m-%Y', 'eu_dash'),
#             ('%m-%d-%Y', 'us_dash'),
#             ('%B %d, %Y', 'us_long'),
#             ('%d %B %Y', 'uk_long')
#         ]
#         self.min_year = 1800
#         self.max_year = 2200
#
#     def is_valid_date(self, year: int, month: int, day: int) -> bool:
#         if not (self.min_year <= year <= self.max_year):
#             return False
#         try:
#             datetime(year, month, day)
#             return True
#         except ValueError:
#             return False
#
#     def detect(self, value: str) -> Tuple[bool, str]:
#         if not isinstance(value, str):
#             return False, "not_string"
#
#         value = value.strip()
#         if not value:
#             return False, "empty"
#
#         # Extremely strict validation against number patterns
#         if re.search(r"^\d{6,}$", value):
#             return False, "too_large_number"
#
#         # Additional prefix/suffix checks to reduce false positives
#         if not re.match(r"^[\d\s/\-.,]+$", value):
#             return False, "invalid_characters"
#
#         # Try specific formats with strict validation
#         for date_format, format_name in self.strict_formats:
#             try:
#                 parsed_date = datetime.strptime(value, date_format)
#                 if self.is_valid_date(parsed_date.year, parsed_date.month, parsed_date.day):
#                     return True, f"valid_{format_name}"
#             except ValueError:
#                 continue
#
#         # Ultra-conservative dateutil parsing
#         try:
#             parsed = parser.parse(value, fuzzy=False, dayfirst=True, yearfirst=False)
#             if self.is_valid_date(parsed.year, parsed.month, parsed.day):
#                 # Extremely strict additional checks
#                 if parsed.strftime(value) == value or parsed.strftime(value.lower()) == value.lower():
#                     return True, "valid_specific_date"
#         except (ValueError, TypeError, OverflowError):
#             pass
#
#         return False, "unparseable_date"
#
#
# class EmailDetector(PatternDetector):
#     def __init__(self):
#         super().__init__("Email", "email", confidence_threshold=99.0)
#
#         # Extremely precise email validation
#         self.local_part_pattern = r'^[a-zA-Z0-9._%+-]{1,64}$'
#         self.domain_pattern = r'^[a-zA-Z0-9-]{1,63}(?:\.[a-zA-Z0-9-]{1,63})*\.[a-zA-Z]{2,}$'
#
#         self.suspicious_patterns = {
#             'repeated_chars': r'(.)\1{4,}',
#             'numeric_domain': r'@\d+\.\d+$',
#             'consecutive_special_chars': r'[._%+-]{2,}'
#         }
#
#     def detect(self, value: str) -> Tuple[bool, str]:
#         if not isinstance(value, str):
#             return False, "not_string"
#
#         value = value.strip().lower()
#
#         # Quick rejection for invalid length and character set
#         if not value or len(value) > 320:
#             return False, "invalid_length"
#
#         try:
#             local_part, domain = value.split('@')
#         except ValueError:
#             return False, "missing_at_symbol"
#
#         # Validate local part
#         if not re.match(self.local_part_pattern, local_part):
#             return False, "invalid_local_part"
#
#         # Validate domain
#         if not re.match(self.domain_pattern, domain):
#             return False, "invalid_domain"
#
#         # Check for suspicious patterns
#         for pattern_name, pattern in self.suspicious_patterns.items():
#             if re.search(pattern, value):
#                 return False, f"suspicious_{pattern_name}"
#
#         return True, "valid_email"
#
#
# class PhoneDetector(PatternDetector):
#     def __init__(self):
#         super().__init__("Phone", "phone", confidence_threshold=99.0)
#
#         # Strict international and national phone number patterns
#         self.patterns = [
#             r'^(\+?1\s?)?(\(\d{3}\)|\d{3})[\s.-]?\d{3}[\s.-]?\d{4}$',  # US/Canada
#             r'^(\+?44\s?7\d{3}|\(?07\d{3}\)?)\s?\d{3}\s?\d{3}$',  # UK Mobile
#             r'^(\+?49\s?\(0\)\s?\d{3,4}|\+?49\s?\d{3,4})\s?\d{3,4}\s?\d{3,4}$',  # German
#             r'^(\+?86\s?1[3-9]\d{9})$',  # China Mobile
#             r'^(\+?91\s?[6-9]\d{9})$'  # India Mobile
#         ]
#
#     def detect(self, value: str) -> Tuple[bool, str]:
#         if not isinstance(value, str):
#             return False, "not_string"
#
#         # Remove all whitespace and formatting
#         clean_value = re.sub(r'[\s\(\)\-\.]', '', value)
#
#         # Direct pattern matching
#         for pattern in self.patterns:
#             if re.match(pattern, value):
#                 return True, "valid_national_phone"
#
#         # Advanced library validation
#         try:
#             parsed = phonenumbers.parse(clean_value, None)
#
#             # Extremely strict validation
#             if not phonenumbers.is_possible_number(parsed):
#                 return False, "impossible_number"
#
#             if phonenumbers.is_valid_number(parsed):
#                 region = phonenumbers.region_code_for_number(parsed)
#                 number_type = phonenumbers.number_type(parsed)
#
#                 type_map = {
#                     phonenumbers.PhoneNumberType.MOBILE: "mobile",
#                     phonenumbers.PhoneNumberType.FIXED_LINE: "fixed_line",
#                     phonenumbers.PhoneNumberType.VOIP: "voip"
#                 }
#
#                 type_label = type_map.get(number_type, "other")
#                 return True, f"valid_{type_label}_{region}"
#
#         except phonenumbers.NumberParseException:
#             pass
#
#         return False, "invalid_phone"
#
#
# class CreditCardDetector(PatternDetector):
#     def __init__(self, confidence_threshold: float = 99.0):
#         super().__init__("Credit Card", "credit_card", confidence_threshold)
#         self.patterns = {
#             'visa': r'^4[0-9]{12}(?:[0-9]{3})?(?:[0-9]{3})?$',
#             'mastercard': r'^(?:5[1-5][0-9]{14}|2(?:2(?:2[1-9]|[3-9][0-9])|[3-6][0-9][0-9]|7(?:[01][0-9]|20))[0-9]{12})$',
#             'amex': r'^3[47][0-9]{13}$',
#             'discover': r'^(?:6011|65[0-9]{2}|64[4-9][0-9]|622(?:12[6-9]|1[3-9][0-9]|[2-8][0-9]{2}|9[01][0-9]|92[0-5])[0-9]{10})$',
#             'diners': r'^3(?:0[0-5]|[68][0-9])[0-9]{11}$',
#             'jcb': r'^(?:2131|1800|35\d{3})\d{11}$',
#             'unionpay': r'^(62[0-9]{14,17})$'
#         }
#         self.test_numbers = {
#             '4111111111111111',
#             '5555555555554444',
#             '378282246310005',
#             '6011111111111117'
#         }
#
#     def detect(self, value: str) -> Tuple[bool, str]:
#         if not isinstance(value, str):
#             return False, "not_string"
#
#         # Remove non-numeric characters
#         cleaned = re.sub(r'\D', '', value)
#
#         if not cleaned:
#             return False, "empty"
#
#         # Check length
#         if not (13 <= len(cleaned) <= 19):
#             return False, "invalid_length"
#
#         # Exclude test numbers
#         if cleaned in self.test_numbers:
#             return False, "test_number"
#
#         # Validate against patterns and Luhn algorithm
#         for card_type, pattern in self.patterns.items():
#             if re.match(pattern, cleaned):
#                 if self._luhn_check(cleaned):
#                     return True, f"valid_{card_type}"
#                 return False, "luhn_check_failed"
#
#         return False, "invalid_format"
#
#     def _luhn_check(self, card_number: str) -> bool:
#         """Enhanced Luhn algorithm check"""
#         try:
#             digits = [int(d) for d in card_number]
#             odd_digits = digits[-1::-2]
#             even_digits = digits[-2::-2]
#             checksum = sum(odd_digits)
#             for d in even_digits:
#                 checksum += sum(divmod(d * 2, 10))
#             return checksum % 10 == 0
#         except (ValueError, IndexError):
#             return False
#
#     def _mask_card_number(self, number: str) -> str:
#         """Mask all but last 4 digits of card number"""
#         cleaned = re.sub(r'\D', '', number)
#         return '*' * (len(cleaned) - 4) + cleaned[-4:]
#
#
#
#
# class CoordinatesDetector(PatternDetector):
#     def __init__(self):
#         super().__init__("Coordinates", DataTypes.COORDINATES.value)
#         # Extended patterns to catch more real-world variations
#         self.patterns = {
#             'decimal': [
#                 r'^-?\d+\.?\d*[,\s]+-?\d+\.?\d*$',  # Basic decimal format
#                 r'^-?\d+°?\d*\'?\d*\.?\d*\"?[NSns][,\s]+-?\d+°?\d*\'?\d*\.?\d*\"?[EWew]$',  # DMS with optional markers
#                 r'^\(\s*-?\d+\.?\d*\s*,\s*-?\d+\.?\d*\s*\)$',  # Parentheses format
#                 r'^-?\d+\.?\d*°?[NSns]?[,\s]+-?\d+\.?\d*°?[EWew]?$'  # Optional degree symbol and hemisphere
#             ],
#             'dms': [
#                 r'^-?\d+°\s*\d+\'\s*\d+(\.\d+)?\"[NSns][,\s]+-?\d+°\s*\d+\'\s*\d+(\.\d+)?\"[EWew]$',
#                 r'^-?\d+°\s*\d+\'\s*\d+(\.\d+)?\"?[NSns]?[,\s]+-?\d+°\s*\d+\'\s*\d+(\.\d+)?\"?[EWew]?$'
#             ]
#         }
#         self.max_precision = 8  # Maximum decimal places
#         self.hemisphere_markers = {'N', 'S', 'E', 'W', 'n', 's', 'e', 'w'}
#
#     def _get_row_counts(self, results: pd.Series) -> Dict[str, int]:
#         """
#         Calculate counts of different validation results
#
#         Args:
#             results: Series of (is_valid, reason) tuples
#
#         Returns:
#             Dictionary mapping validation reasons to their counts
#         """
#         reasons = pd.DataFrame(results.tolist(), columns=['valid', 'reason'])
#         return dict(reasons['reason'].value_counts())
#
#     def analyze_column(self, series: pd.Series) -> DetectionResult:
#         total_rows = len(series.dropna())
#         if total_rows == 0:
#             return self._create_empty_result()
#
#         # Convert to string and clean
#         str_series = series.astype(str).str.strip()
#
#         # Check each value
#         results = str_series.apply(self._check_value)
#         valid_mask = results.apply(lambda x: x[0])
#
#         # Calculate match percentage
#         match_percentage = (valid_mask.sum() / total_rows) * 100
#
#         if match_percentage >= 98:
#             consistent_samples = str_series[valid_mask].head(3).tolist()
#             inconsistent_samples = str_series[~valid_mask].head(3).tolist()
#         else:
#             match_percentage = 0
#             consistent_samples = []
#             inconsistent_samples = str_series.head(3).tolist()
#
#         return DetectionResult(
#             column_type=self.pattern_type,
#             match_percentage=match_percentage,
#             consistent_samples=consistent_samples,
#             inconsistent_samples=inconsistent_samples,
#             inconsistency_percentage=100 - match_percentage,
#             total_rows=total_rows,
#             row_counts=self._get_row_counts(results)
#         )
#
#     def _check_value(self, value: str) -> Tuple[bool, str]:
#         if not isinstance(value, str):
#             return False, "not_string"
#
#         value = value.strip()
#         if not value:
#             return False, "empty"
#
#         # Try decimal format first
#         for pattern in self.patterns['decimal']:
#             if re.match(pattern, value):
#                 coords = self._extract_decimal_coords(value)
#                 if coords:
#                     lat, lon = coords
#                     if self._validate_coordinates(lat, lon):
#                         return True, "valid_decimal"
#
#         # Try DMS format
#         for pattern in self.patterns['dms']:
#             if re.match(pattern, value):
#                 coords = self._parse_dms(value)
#                 if coords:
#                     lat, lon = coords
#                     if self._validate_coordinates(lat, lon):
#                         return True, "valid_dms"
#
#         return False, "invalid_format"
#
#     def _extract_decimal_coords(self, value: str) -> Optional[Tuple[float, float]]:
#         """Extract decimal coordinates handling various formats"""
#         try:
#             # Remove parentheses and split
#             cleaned = value.replace('(', '').replace(')', '')
#             parts = re.split(r'[,\s]+', cleaned)
#
#             # Extract numbers and hemispheres
#             coords = []
#             for part in parts:
#                 # Remove degree symbols and handle hemispheres
#                 part = part.replace('°', '')
#                 hemisphere = None
#                 if part[-1] in self.hemisphere_markers:
#                     hemisphere = part[-1].upper()
#                     part = part[:-1]
#
#                 coord = float(part)
#                 if hemisphere in ['S', 'W']:
#                     coord = -coord
#                 coords.append(coord)
#
#             if len(coords) == 2:
#                 return coords[0], coords[1]
#
#         except (ValueError, IndexError):
#             pass
#         return None
#
#     def _validate_coordinates(self, lat: float, lon: float) -> bool:
#         """Validate coordinate ranges and precision"""
#         try:
#             if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
#                 return False
#
#             # Check precision
#             lat_str, lon_str = f"{lat:.10f}", f"{lon:.10f}"
#             if (len(lat_str.split('.')[-1]) > self.max_precision or
#                     len(lon_str.split('.')[-1]) > self.max_precision):
#                 return False
#
#             return True
#         except (ValueError, TypeError):
#             return False
#
#     def _parse_dms(self, dms_str: str) -> Optional[Tuple[float, float]]:
#         """Parse degrees-minutes-seconds format with various notations"""
#         try:
#             parts = re.split(r'[,\s]+', dms_str)
#             if len(parts) != 2:
#                 return None
#
#             lat_dms = self._parse_dms_part(parts[0], ['N', 'S'])
#             lon_dms = self._parse_dms_part(parts[1], ['E', 'W'])
#
#             if lat_dms is not None and lon_dms is not None:
#                 return lat_dms, lon_dms
#         except (ValueError, IndexError):
#             pass
#         return None
#
#     def _parse_dms_part(self, dms_str: str, hemispheres: List[str]) -> Optional[float]:
#         """Parse individual DMS component"""
#         pattern = r'(-?\d+)°\s*(\d+)\'\s*(\d+(?:\.\d+)?)\"?([NSEWnsew])?'
#         match = re.match(pattern, dms_str)
#         if not match:
#             return None
#
#         d, m, s, h = match.groups()
#         result = float(d) + float(m) / 60 + float(s) / 3600
#
#         if h and h.upper() in hemispheres[1]:  # S or W
#             result = -result
#
#         return result
#
#
# class IPAddressDetector(PatternDetector):
#     def __init__(self):
#         super().__init__("IP Address", DataTypes.IP_ADDRESS.value)
#         # Enhanced IPv4 pattern
#         self.ipv4_pattern = r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
#
#         # Enhanced IPv6 pattern with all variations
#         self.ipv6_pattern = r'^(?:' + '|'.join([
#             r'(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}',  # 1:2:3:4:5:6:7:8
#             r'(?:[0-9a-fA-F]{1,4}:){1,7}:',  # 1:: or 1:2:3:4:5:6:7::
#             r'(?:[0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}',  # 1::8 or 1:2:3:4:5:6::8
#             r'(?:[0-9a-fA-F]{1,4}:){1,5}(?::[0-9a-fA-F]{1,4}){1,2}',  # 1::7:8 or 1:2:3:4:5::7:8
#             r'(?:[0-9a-fA-F]{1,4}:){1,4}(?::[0-9a-fA-F]{1,4}){1,3}',  # 1::6:7:8 or 1:2:3:4::6:7:8
#             r'(?:[0-9a-fA-F]{1,4}:){1,3}(?::[0-9a-fA-F]{1,4}){1,4}',  # 1::5:6:7:8 or 1:2:3::5:6:7:8
#             r'(?:[0-9a-fA-F]{1,4}:){1,2}(?::[0-9a-fA-F]{1,4}){1,5}',  # 1::4:5:6:7:8 or 1:2::4:5:6:7:8
#             r'[0-9a-fA-F]{1,4}:(?:(?::[0-9a-fA-F]{1,4}){1,6})',  # 1::3:4:5:6:7:8
#             r':(?:(?::[0-9a-fA-F]{1,4}){1,7}|:)',  # ::2:3:4:5:6:7:8 or ::
#             r'fe80:(?::[0-9a-fA-F]{0,4}){0,4}%[0-9a-zA-Z]{1,}',  # fe80::7:8%eth0
#             r'::(?:ffff(?::0{1,4}){0,1}:){0,1}(?:(?:25[0-5]|(?:2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}(?:25[0-5]|(?:2[0-4]|1{0,1}[0-9]){0,1}[0-9])',
#             # ::255.255.255.255
#             r'(?:[0-9a-fA-F]{1,4}:){1,4}:(?:(?:25[0-5]|(?:2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}(?:25[0-5]|(?:2[0-4]|1{0,1}[0-9]){0,1}[0-9])'
#             # 2001:db8:3:4::192.0.2.33
#         ]) + ')$'
#
#         # Define reserved IP ranges
#         self.reserved_ranges: Dict[str, List[Tuple[Union[IPv4Address, IPv6Address], str]]] = {
#             'private_ipv4': [
#                 (ip_network('10.0.0.0/8'), "private_range"),
#                 (ip_network('172.16.0.0/12'), "private_range"),
#                 (ip_network('192.168.0.0/16'), "private_range")
#             ],
#             'loopback': [(ip_network('127.0.0.0/8'), "loopback")],
#             'link_local': [(ip_network('169.254.0.0/16'), "link_local")],
#             'multicast': [(ip_network('224.0.0.0/4'), "multicast")],
#             'reserved': [(ip_network('240.0.0.0/4'), "reserved")]
#         }
#
#     def detect(self, value: str) -> Tuple[bool, str]:
#         """
#         Detect and validate IP addresses.
#
#         Args:
#             value: String to validate as an IP address
#
#         Returns:
#             Tuple[bool, str]: (is_valid, status_message)
#         """
#         if not isinstance(value, str):
#             return False, "not_string"
#
#         value = value.strip()
#         if not value:
#             return False, "empty"
#
#         try:
#             ip_addr = ip_address(value)
#
#             if isinstance(ip_addr, IPv4Address):
#                 if not re.match(self.ipv4_pattern, value):
#                     return False, "invalid_ipv4_format"
#
#                 # Check for special ranges
#                 for range_type, networks in self.reserved_ranges.items():
#                     for network, range_name in networks:
#                         if ip_addr in network:
#                             return True, f"valid_ipv4_{range_name}"
#
#                 return True, "valid_ipv4_public"
#
#             elif isinstance(ip_addr, IPv6Address):
#                 if not re.match(self.ipv6_pattern, value):
#                     return False, "invalid_ipv6_format"
#
#                 if ip_addr.is_link_local:
#                     return True, "valid_ipv6_link_local"
#                 elif ip_addr.is_private:
#                     return True, "valid_ipv6_private"
#                 elif ip_addr.is_loopback:
#                     return True, "valid_ipv6_loopback"
#                 elif ip_addr.is_multicast:
#                     return True, "valid_ipv6_multicast"
#                 elif ip_addr.is_reserved:
#                     return True, "valid_ipv6_reserved"
#
#                 return True, "valid_ipv6_public"
#
#         except ValueError:
#             return False, "invalid_ip"
#
#         return False, "invalid_format"
#
#
# class PostalCodeDetector(PatternDetector):
#     def __init__(self):
#         super().__init__("Postal Code", DataTypes.POSTAL_CODE.value)
#         self.patterns = {
#             'US': r'^\d{5}(?:-\d{4})?$',
#             'UK': r'^[A-Z]{1,2}[0-9][A-Z0-9]? ?[0-9][A-Z]{2}$',
#             'CA': r'^[ABCEGHJ-NPRSTVXY]\d[ABCEGHJ-NPRSTV-Z] ?\d[ABCEGHJ-NPRSTV-Z]\d$',
#             'AU': r'^\d{4}$',
#             'DE': r'^\d{5}$',
#             'FR': r'^\d{5}$',
#             'IT': r'^\d{5}$',
#             'JP': r'^\d{3}-\d{4}$',
#             'BR': r'^\d{5}-?\d{3}$',
#             'IN': r'^\d{6}$'
#         }
#
#         # Invalid patterns for edge cases
#         self.invalid_patterns = {
#             'US': [r'^00000', r'^99999', r'^12345-6789'],
#             'UK': [r'^QQ', r'^XX'],
#             'CA': [r'^[DFIOQU]'],
#         }
#
#         # Exclusion patterns to prevent confusion with phone numbers
#         self.exclusion_patterns = [
#             r'^\+?\d{1,4}[\s.-]?\(?\d{1,4}\)?[\s.-]?\d{3,}$',  # Matches phone-like formats
#             r'^\d{3}[-.\s]?\d{3}[-.\s]?\d{4,}$'  # US phone formats
#         ]
#
#     def detect(self, value: str) -> Tuple[bool, str]:
#         if not isinstance(value, str):
#             return False, "not_string"
#
#         value = value.strip().upper()
#         if not value:
#             return False, "empty"
#
#         # Exclude phone-like formats
#         for exclusion_pattern in self.exclusion_patterns:
#             if re.match(exclusion_pattern, value):
#                 return False, "possible_phone_format"
#
#         # Match against postal code patterns
#         for country, pattern in self.patterns.items():
#             if re.match(pattern, value):
#                 # Check for invalid patterns
#                 if country in self.invalid_patterns:
#                     for invalid_pattern in self.invalid_patterns[country]:
#                         if re.match(invalid_pattern, value):
#                             return False, f"invalid_{country.lower()}_pattern"
#
#                 # Additional country-specific validations
#                 if country == 'US':
#                     if value.startswith('00') or value.startswith('99'):
#                         return False, "invalid_us_prefix"
#                 elif country == 'UK':
#                     outward = value.split()[0]
#                     if len(outward) > 4:
#                         return False, "invalid_uk_outward"
#                 elif country == 'CA':
#                     if value[0] in 'DFIOQU' or value[1] == '0':
#                         return False, "invalid_ca_fsa"
#
#                 return True, f"valid_{country.lower()}"
#
#         return False, "invalid_format"
#
#
# class SSNDetector(PatternDetector):
#     def __init__(self):
#         super().__init__("SSN", "ssn")
#         self.pattern = r'^\d{3}-\d{2}-\d{4}$|^\d{9}$'
#         self.invalid_prefixes = {'000', '666', '900', '999'}
#
#     def detect(self, value: str) -> Tuple[bool, str]:
#         if not isinstance(value, str):
#             return False, "not_string"
#
#         # Clean the input
#         cleaned = re.sub(r'[\s\-]', '', value)
#
#         if len(cleaned) != 9:
#             return False, "invalid_length"
#
#         if not cleaned.isdigit():
#             return False, "non_numeric"
#
#         if cleaned[:3] in self.invalid_prefixes:
#             return False, "invalid_prefix"
#
#         if cleaned[3:5] == '00' or cleaned[5:] == '0000':
#             return False, "invalid_sequence"
#
#         return True, "valid"
#
#
# class DataQualityDetector:
#     def __init__(self, df: pd.DataFrame):
#         self.df = df
#         # Define detectors in strict priority order
#         self.detector_hierarchy = [
#             {
#                 'category': 'Date',
#                 'detectors': [DateDetector()]
#             },
#             {
#                 'category': 'Identifiers',
#                 'detectors': [
#                     EmailDetector(),
#                     CreditCardDetector(),
#                     SSNDetector(),
#                     PhoneDetector()
#                 ]
#             },
#             {
#                 'category': 'Location',
#                 'detectors': [
#                     CoordinatesDetector(),
#                     IPAddressDetector(),
#                     PostalCodeDetector()
#                 ]
#             },
#             {
#                 'category': 'Financial',
#                 'detectors': [CurrencyCodeDetector()]
#             }
#         ]
#
#     def analyze(self) -> Dict[str, Any]:
#         results = {}
#         unclassified_columns: Set[str] = set(self.df.columns)
#
#         # Process each category of detectors in order
#         for detector_group in self.detector_hierarchy:
#             if not unclassified_columns:  # Stop if all columns are classified
#                 break
#
#             newly_classified = self._process_detector_group(
#                 detector_group['detectors'],
#                 unclassified_columns
#             )
#
#             # Remove classified columns from the unclassified set
#             unclassified_columns -= newly_classified.keys()
#
#             # Add results to the main results dictionary
#             results.update(newly_classified)
#
#         # Handle any remaining unclassified columns
#         for column in unclassified_columns:
#             results[column] = self._create_unknown_result(column)
#
#         return results
#
#     def _process_detector_group(
#             self,
#             detectors: List[Any],
#             columns: Set[str]
#     ) -> Dict[str, Any]:
#         """
#         Process a group of detectors against the remaining unclassified columns.
#         Returns a dictionary of newly classified columns and their results.
#         """
#         classified_columns = {}
#
#         for column in columns:
#             for detector in detectors:
#                 result = detector.analyze_column(self.df[column])
#
#                 if result.match_percentage > self._get_threshold(detector):
#                     classified_columns[column] = {
#                         'detector_type': detector.pattern_type,
#                         'match_percentage': result.match_percentage,
#                         'consistent_samples': result.consistent_samples,
#                         'inconsistent_samples': result.inconsistent_samples,
#                         'inconsistency_percentage': result.inconsistency_percentage,
#                         'total_rows': result.total_rows,
#                         'detection_details': result.row_counts
#                     }
#                     break  # Stop testing this column once a match is found
#
#         return classified_columns
#
#     def _get_threshold(self, detector: Any) -> float:
#         """
#         Returns the match threshold for a given detector.
#         Can be customized based on detector type.
#         """
#         # Example thresholds - adjust these based on your needs
#         thresholds = {
#             'DateDetector': 0.95,
#             'EmailDetector': 0.95,
#             'CreditCardDetector': 0.98,
#             'SSNDetector': 0.98,
#             'PhoneDetector': 0.95,
#             'CoordinatesDetector': 0.95,
#             'IPAddressDetector': 0.95,
#             'PostalCodeDetector': 0.95,
#             'CurrencyCodeDetector': 0.95,
#         }
#         return thresholds.get(detector.__class__.__name__, 0.95)
#
#     def _create_unknown_result(self, column: str) -> Dict[str, Any]:
#         """
#         Creates a result dictionary for columns that couldn't be classified.
#         """
#         return {
#             'detector_type': DataTypes.UNKNOWN.value,
#             'match_percentage': 0,
#             'total_rows': len(self.df[column].dropna()),
#             'sample_values': self.df[column].dropna().head(3).tolist()
#         }
#
#
#
# # Create comprehensive test data with consistent sample size and edge cases
# test_data = {
#     'email': [
#         'user@example.com',  # Valid standard email
#         'valid.email+tag@gmail.com',  # Valid email with tags
#         'user.name@subdomain.domain.co.uk',  # Valid email with multiple subdomains
#         'invalid-email',  # Invalid - missing domain
#         'user@domain',  # Invalid - incomplete domain
#         '@domain.com',  # Invalid - missing local part
#         'user@.com',  # Invalid - missing domain part
#         'very.unusual."@".unusual.com',  # Valid but unusual email
#         'disposable@temp.com',  # Valid but disposable domain
#         'user@localhost'  # Invalid - local domain
#     ],
#
#     'phone': [
#         '123-456-7890',  # Valid US format with hyphens
#         '+1 (555) 123-4567',  # Valid US format with country code
#         '+44 20 7123 4567',  # Valid UK format
#         '555-0123',  # Invalid - too short
#         '123456789012345',  # Invalid - too long
#         'invalid',  # Invalid - non-numeric
#         '(800) FLOWERS',  # Invalid - contains letters
#         '+61 2 9876 5432',  # Valid Australian format
#         '+49 30 12345678',  # Valid German format
#         '1234567890'  # Valid US format without formatting
#     ],
#
#     'description': [
#         'This is a comprehensive description that provides meaningful content about a specific topic with sufficient detail.',
#         'Another detailed explanation covering multiple aspects of the subject matter in a clear and concise manner.',
#         'Short text',  # Invalid - too short
#         'a' * 50,  # Invalid - repetitive
#         ' '.join(['word'] * 20),  # Invalid - repetitive words
#         'A properly detailed technical explanation of an important system component that requires documentation.',
#         'The quick brown fox jumps over the lazy dog multiple times creating a lengthy description.',
#         'Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt.',
#         'Detailed insight of system performance metrics indicating several areas for potential improvement.',
#         'In-depth review of project milestones and deliverables including timeline and resource allocation.'
#     ],
#
#     'credit_card': [
#         '4532015112830366',  # Valid Visa
#         '5425233430109903',  # Valid Mastercard
#         '371449635398431',  # Valid American Express
#         '6011111111111117',  # Valid Discover
#         '3530111333300000',  # Valid JCB
#         '4532015112830367',  # Invalid checksum
#         '1234567890123456',  # Invalid number
#         '5610591081018250',  # Invalid format
#         '30569309025904',  # Valid Diners Club
#         '6011000990139424'  # Valid Discover
#     ],
#
#     'category': [
#         'High',  # Common category
#         'Medium',  # Common category
#         'Low',  # Common category
#         'High',  # Repeated value
#         'Medium',  # Repeated value
#         'Critical',  # Less common category
#         'Low',  # Repeated value
#         'Unknown',  # Edge category
#         'Medium',  # Repeated value
#         'High'  # Repeated value
#     ],
#
#     'coordinates': [
#         '40.7128,-74.0060',  # Valid NYC coordinates
#         '51.5074,-0.1278',  # Valid London coordinates
#         '90.0000,180.0000',  # Valid edge case - max values
#         '-90.0000,-180.0000',  # Valid edge case - min values
#         '35°41\'22.1"N,139°41\'30.1"E',  # Valid DMS format
#         '91.0000,45.0000',  # Invalid latitude
#         '45.0000,181.0000',  # Invalid longitude
#         'invalid',  # Invalid format
#         '0.0000,0.0000',  # Valid null island
#         '51°30\'26"N,0°7\'39"W'  # Valid DMS format
#     ],
#
#     'ip_address': [
#         '192.168.1.1',  # Valid private IPv4
#         '10.0.0.1',  # Valid private IPv4
#         '172.16.254.1',  # Valid private IPv4
#         '2001:0db8:85a3::8a2e:370:7334',  # Valid IPv6
#         'fe80::1ff:fe23:4567:890a',  # Valid IPv6 link-local
#         '256.1.2.3',  # Invalid IPv4
#         '2001:0db8:85a3::8a2e:370g:7334',  # Invalid IPv6
#         '192.168.001.1',  # Invalid format
#         '::1',  # Valid IPv6 loopback
#         '8.8.8.8'  # Valid public IPv4
#     ],
#
#     'postal_code': [
#         '12345',  # Valid US
#         'SW1A 1AA',  # Valid UK
#         'M5V 2T6',  # Valid Canada
#         '00000',  # Invalid US
#         'XX1X 1XX',  # Invalid UK
#         '75001',  # Valid France
#         '123456',  # Valid India
#         '100-0001',  # Valid Japan
#         '28010',  # Valid Spain
#         'D04 E9P1'  # Valid Ireland
#     ],
#
#     'currency_code': [
#         'USD',  # Valid US Dollar
#         'EUR',  # Valid Euro
#         'GBP',  # Valid British Pound
#         'JPY',  # Valid Japanese Yen
#         'EURO',  # Invalid - too long
#         'US',  # Invalid - too short
#         'XXX',  # Invalid - non-existent
#         'CHF',  # Valid Swiss Franc
#         'AUD',  # Valid Australian Dollar
#         'CAD'  # Valid Canadian Dollar
#     ],
#
#     'date': [
#         '2024-03-21',  # Valid ISO format
#         '21/03/2024',  # Valid UK format
#         '03/21/2024',  # Valid US format
#         '2024.03.21',  # Valid with dots
#         'March 21, 2024',  # Valid long format
#         '20240321',  # Valid compact format
#         '2024-13-01',  # Invalid month
#         '2024-02-30',  # Invalid day for February
#         '1899-12-31',  # Invalid year (too old)
#         '2101-01-01'  # Invalid year (too future)
#     ],
#
#     'numeric': [
#         '123.45',  # Valid decimal
#         '1,234.56',  # Valid with thousands separator
#         '-987.65',  # Valid negative
#         '1.23e-4',  # Valid scientific notation
#         '99.999%',  # Valid percentage
#         '1.234.567,89',  # Valid European format
#         'invalid',  # Invalid non-numeric
#         '1e309',  # Invalid overflow
#         '0.1234567890123',  # Invalid too many decimals
#         '1,234,567.89'  # Valid with multiple separators
#     ]
# }
#
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
#
# # Record start time
# start_time = time.time()
# print(f"Analysis started at: {datetime.fromtimestamp(start_time).strftime('%Y-%m-%d %H:%M:%S')}")
#
# # Your existing code
# file_path = r"C:\Users\admin\Downloads\fifa21_raw_data_v2.csv"
# df = pd.read_csv(file_path, encoding='utf-8')
# #df = pd.DataFrame(test_data)
# print(df.head())
#
# # Create detector instance
# detector = DataQualityDetector(df)
#
# # Run insight
# results = detector.analyze()
#
# # Record end time
# end_time = time.time()
# execution_time = end_time - start_time
#
# # Print timing information
# print("\nTiming Information:")
# print("=" * 80)
# print(f"Start Time: {datetime.fromtimestamp(start_time).strftime('%Y-%m-%d %H:%M:%S')}")
# print(f"End Time: {datetime.fromtimestamp(end_time).strftime('%Y-%m-%d %H:%M:%S')}")
# print(f"Total Execution Time: {format_time(execution_time)}")
# print("=" * 80)
#
# # Print detailed results with explanation of edge cases
# print("\nEnhanced Data Quality Analysis Results:")
# print("=" * 80)
# for column, result in results.items():
#     print(f"\nColumn: {column}")
#     print(f"Detected Type: {result['detector_type']}")
#     print(f"Match Percentage: {result['match_percentage']:.2f}%")
#     print("\nConsistent Samples (Valid):")
#     if 'consistent_samples' in result:
#         for sample in result['consistent_samples']:
#             print(f"  - {sample}")
#     print("\nInconsistent Samples (Invalid/Edge Cases):")
#     if 'inconsistent_samples' in result:
#         for sample in result['inconsistent_samples']:
#             print(f"  - {sample}")
#     if 'detection_details' in result:
#         print("\nDetection Details:")
#         for key, value in result['detection_details'].items():
#             if isinstance(value, (int, float)):
#                 print(f"  {key}: {value}")
#     print("-" * 80)