from django.db import models
import json

# Create your models here.

class ComparisonJob(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    file1 = models.FileField(upload_to='uploads/')
    file2 = models.FileField(upload_to='uploads/')
    comparison_fields = models.JSONField()
    status = models.CharField(max_length=20, default='pending')
    result = models.JSONField(null=True, blank=True)

    def __str__(self):
        return f"Comparison {self.id} ({self.status})"

class FieldMapping(models.Model):
    field_type = models.CharField(max_length=100, unique=True)
    variations = models.JSONField(help_text='List of possible column names for this field type')
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.field_type} ({len(self.get_variations())} variations)"

    def get_variations(self):
        return self.variations if isinstance(self.variations, list) else json.loads(self.variations)

    def add_variation(self, variation):
        variations = self.get_variations()
        if variation.lower() not in [v.lower() for v in variations]:
            variations.append(variation)
            self.variations = json.dumps(variations)
            self.save()

    @classmethod
    def get_field_mapping(cls):
        """Convert all active field mappings to dictionary format"""
        mapping_dict = {}
        for mapping in cls.objects.filter(is_active=True):
            mapping_dict[mapping.field_type.lower()] = mapping.get_variations()
        return mapping_dict

    class Meta:
        indexes = [
            models.Index(fields=['field_type']),
        ]
