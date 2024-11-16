import pandas as pd
import json
import magic
from typing import Dict, List, Tuple, Any
from fuzzywuzzy import fuzz
import re

class FileComparerService:
    def __init__(self):
        self.field_mappings = {}
        self.load_field_mappings()

    def load_field_mappings(self):
        """Load field mappings from database"""
        from .models import FieldMapping
        mappings = FieldMapping.objects.filter(is_active=True)
        for mapping in mappings:
            self.field_mappings[mapping.field_type.lower()] = mapping.variations

    @staticmethod
    def detect_file_type(file_path: str) -> str:
        mime = magic.Magic(mime=True)
        file_type = mime.from_file(file_path)
        return file_type

    @staticmethod
    def read_file(file_path: str) -> pd.DataFrame:
        file_type = FileComparerService.detect_file_type(file_path)
        
        if 'csv' in file_type:
            return pd.read_csv(file_path)
        elif 'excel' in file_type or 'spreadsheet' in file_type:
            return pd.read_excel(file_path)
        elif 'json' in file_type:
            with open(file_path, 'r') as f:
                data = json.load(f)
            return pd.json_normalize(data)
        else:
            raise ValueError(f"Unsupported file type: {file_type}")

    def set_field_mappings(self, mappings: Dict[str, List[str]]):
        """Set field mappings for comparison"""
        self.field_mappings = mappings

    def add_field_mapping(self, field_type: str, variations: List[str]):
        """Add or update a field mapping"""
        self.field_mappings[field_type.lower()] = variations

    def get_field_mappings(self):
        """Get all field mappings."""
        from .models import FieldMapping
        return FieldMapping.objects.filter(is_active=True).order_by('field_type')

    def add_field_mapping_db(self, field_type, variations):
        """Add a new field mapping."""
        from .models import FieldMapping
        mapping = FieldMapping.objects.create(
            field_type=field_type,
            variations=variations
        )
        # Reload mappings after adding new one
        self.load_field_mappings()
        return mapping

    def update_field_mapping(self, mapping_id, field_type, variations):
        """Update an existing field mapping."""
        from .models import FieldMapping
        mapping = FieldMapping.objects.get(id=mapping_id)
        mapping.field_type = field_type
        mapping.variations = variations
        mapping.save()
        # Reload mappings after update
        self.load_field_mappings()
        return mapping

    def delete_field_mapping(self, mapping_id):
        """Delete a field mapping."""
        from .models import FieldMapping
        mapping = FieldMapping.objects.get(id=mapping_id)
        mapping.delete()
        # Reload mappings after deletion
        self.load_field_mappings()

    def find_matching_column(self, df: pd.DataFrame, field_type: str) -> str:
        """Find the actual column name in the dataframe that matches a field type"""
        df_columns_lower = {col.lower(): col for col in df.columns}
        
        # Try exact match first
        if field_type.lower() in df_columns_lower:
            return df_columns_lower[field_type.lower()]
        
        # Check known mappings
        possible_names = self.field_mappings.get(field_type.lower(), [])
        for name in possible_names:
            if name.lower() in df_columns_lower:
                return df_columns_lower[name.lower()]
        
        # Try fuzzy matching
        best_match = None
        best_score = 0
        threshold = 80  # Minimum similarity score to consider a match

        for col in df.columns:
            score = fuzz.ratio(field_type.lower(), col.lower())
            if score > best_score and score >= threshold:
                best_score = score
                best_match = col

        if best_match:
            return best_match
        
        raise ValueError(f"Could not find matching column for field type: {field_type}")

    def detect_column_type(self, series: pd.Series) -> str:
        """Detect the type of data in a column based on its values"""
        # Convert to string and get non-null values for analysis
        sample = series.astype(str).dropna().head(100)  # Sample first 100 non-null values
        if len(sample) == 0:
            return 'unknown'

        # Helper function to check if string could be a date
        def is_date_format(s):
            date_patterns = [
                r'\d{4}-\d{2}-\d{2}',  # YYYY-MM-DD
                r'\d{2}-\d{2}-\d{4}',  # DD-MM-YYYY
                r'\d{2}/\d{2}/\d{4}',  # DD/MM/YYYY
                r'\d{4}/\d{2}/\d{2}',  # YYYY/MM/DD
                r'\d{2}\.\d{2}\.\d{4}'  # DD.MM.YYYY
            ]
            return any(re.search(pattern, s) for pattern in date_patterns)

        # Helper function to check if string is numeric
        def is_numeric(s):
            try:
                float(s.replace(',', ''))
                return True
            except ValueError:
                return False

        # Check for common patterns
        numeric_count = sum(1 for x in sample if is_numeric(x))
        date_count = sum(1 for x in sample if is_date_format(x))
        id_pattern_count = sum(1 for x in sample if re.match(r'^[A-Za-z0-9-_]+$', x))
        
        # Calculate percentages
        total = len(sample)
        numeric_pct = numeric_count / total
        date_pct = date_count / total
        id_pattern_pct = id_pattern_count / total

        # Determine type based on patterns
        if date_pct > 0.7:
            return 'date'
        elif numeric_pct > 0.7:
            # Check if it's likely an ID (mostly sequential numbers)
            try:
                nums = pd.to_numeric(sample)
                if nums.is_monotonic_increasing and nums.diff().dropna().std() < 1:
                    return 'id'
                return 'numeric'
            except:
                return 'text'
        elif id_pattern_pct > 0.7:
            return 'id'
        
        return 'text'

    def suggest_field_mappings(self, df1: pd.DataFrame, df2: pd.DataFrame) -> List[Dict[str, Any]]:
        """Suggest possible field mappings between two dataframes"""
        suggestions = []
        
        # Common field type keywords and their categories
        field_categories = {
            'id': ['id', 'identifier', 'key', 'code', 'no', 'number'],
            'date': ['date', 'time', 'datetime', 'timestamp'],
            'amount': ['amount', 'sum', 'total', 'price', 'value', 'payment'],
            'account': ['account', 'acct', 'acc'],
            'transaction': ['transaction', 'trans', 'trx'],
            'description': ['description', 'desc', 'details', 'note', 'memo'],
            'status': ['status', 'state', 'condition'],
            'type': ['type', 'category', 'kind'],
            'name': ['name', 'title', 'label']
        }

        def get_field_category(field_name: str) -> set:
            """Get the categories a field might belong to based on its name"""
            field_lower = field_name.lower()
            categories = set()
            
            # Check each category's keywords
            for category, keywords in field_categories.items():
                for keyword in keywords:
                    if keyword in field_lower:
                        categories.add(category)
                        break
            
            return categories

        def calculate_similarity(col1: str, col2: str, type1: str, type2: str) -> float:
            """Calculate similarity score between two column names and their data types"""
            # Get categories for both columns
            cat1 = get_field_category(col1)
            cat2 = get_field_category(col2)
            
            # Base string similarity
            string_similarity = fuzz.ratio(col1.lower(), col2.lower()) / 100.0
            
            # Category match bonus
            category_match = len(cat1.intersection(cat2)) > 0
            category_bonus = 0.3 if category_match else 0
            
            # Category mismatch penalty
            category_mismatch = len(cat1) > 0 and len(cat2) > 0 and len(cat1.intersection(cat2)) == 0
            category_penalty = 0.5 if category_mismatch else 0
            
            # Data type match/mismatch
            type_match = type1 == type2
            type_penalty = 0.8 if not type_match else 0
            
            # Special case: if one is date and other is not, severely penalize
            if ('date' in (type1, type2)) and type1 != type2:
                type_penalty = 0.9
            
            # Final score
            final_score = string_similarity + category_bonus - category_penalty - type_penalty
            
            # Ensure score is between 0 and 1
            return max(0, min(1, final_score))

        # Cache column types
        col_types1 = {col: self.detect_column_type(df1[col]) for col in df1.columns}
        col_types2 = {col: self.detect_column_type(df2[col]) for col in df2.columns}

        # Generate suggestions with improved matching
        for col1 in df1.columns:
            best_match = None
            best_score = 0
            
            for col2 in df2.columns:
                score = calculate_similarity(col1, col2, col_types1[col1], col_types2[col2])
                if score > best_score:
                    best_score = score
                    best_match = col2
            
            # Only suggest matches with high enough confidence
            if best_score >= 0.4:  # Lower threshold since we're stricter now
                suggestions.append({
                    'field1': col1,
                    'field2': best_match,
                    'confidence': int(best_score * 100),
                    'type1': col_types1[col1],
                    'type2': col_types2[best_match]
                })
        
        return suggestions

    def normalize_value(self, value: Any) -> str:
        """Normalize values for comparison by removing extra spaces and converting to string"""
        if pd.isna(value):
            return ''
        return str(value).strip().lower()

    def compare_files(self, file1_path, file2_path, fields):
        """Compare two files based on specified field mappings."""
        try:
            # Read files
            df1 = self.read_file(file1_path)
            df2 = self.read_file(file2_path)
            
            results = {
                'total_rows': {
                    'file1': len(df1),
                    'file2': len(df2)
                },
                'differences': []
            }
            
            # Compare each field mapping
            for source_field, target_field in fields.items():
                if source_field in df1.columns and target_field in df2.columns:
                    # Get unique values from both fields
                    values1 = set(df1[source_field].dropna().astype(str))
                    values2 = set(df2[target_field].dropna().astype(str))
                    
                    # Find matching and different values
                    matching_values = values1.intersection(values2)
                    only_in_file1 = values1 - values2
                    only_in_file2 = values2 - values1
                    
                    # Get rows with different values
                    different_values = []
                    merged = pd.merge(df1[[source_field]], df2[[target_field]], 
                                    left_on=source_field, right_on=target_field, 
                                    how='outer', indicator=True)
                    
                    # Find rows that don't match
                    diff_rows = merged[merged['_merge'] != 'both']
                    for _, row in diff_rows.iterrows():
                        different_values.append({
                            'file1_value': str(row[source_field]) if pd.notna(row[source_field]) else None,
                            'file2_value': str(row[target_field]) if pd.notna(row[target_field]) else None
                        })
                    
                    field_diff = {
                        'field_type': source_field,
                        'file1_field': source_field,
                        'file2_field': target_field,
                        'matching_values': list(matching_values),
                        'only_in_file1': list(only_in_file1),
                        'only_in_file2': list(only_in_file2),
                        'different_values': different_values
                    }
                    
                    results['differences'].append(field_diff)
                else:
                    # Handle missing columns
                    results['differences'].append({
                        'field_type': source_field,
                        'file1_field': source_field,
                        'file2_field': target_field,
                        'error': f"Column not found: {source_field if source_field not in df1.columns else target_field}"
                    })
            
            return results
            
        except Exception as e:
            raise Exception(f"Error comparing files: {str(e)}")
