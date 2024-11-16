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

class ScheduledTask(models.Model):
    FREQUENCY_CHOICES = [
        ('hourly', 'Hourly'),
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('paused', 'Paused'),
        ('error', 'Error'),
    ]

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    source_path = models.CharField(max_length=500)
    target_path = models.CharField(max_length=500)
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES)
    comparison_fields = models.JSONField()
    last_run = models.DateTimeField(null=True, blank=True)
    next_run = models.DateTimeField(auto_now_add=True)  # Initialize to current time
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE, null=True, blank=True)
    
    def __str__(self):
        return f"{self.name} ({self.frequency})"

    class Meta:
        indexes = [
            models.Index(fields=['status', 'next_run']),
        ]

class ComparisonHistory(models.Model):
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    file1 = models.CharField(max_length=255)
    file2 = models.CharField(max_length=255)
    comparison_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=[
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('in_progress', 'In Progress')
    ])
    differences_found = models.IntegerField(default=0)
    execution_time = models.FloatField(help_text='Execution time in seconds', null=True, blank=True)

    class Meta:
        ordering = ['-comparison_date']

class UserStats(models.Model):
    user = models.OneToOneField('auth.User', on_delete=models.CASCADE)
    total_comparisons = models.IntegerField(default=0)
    last_comparison_date = models.DateTimeField(null=True, blank=True)
    subscription_type = models.CharField(max_length=50, default='Free')
    comparisons_this_month = models.IntegerField(default=0)
    total_time_saved = models.FloatField(default=0, help_text='Time saved in hours')
    
    def __str__(self):
        return f"Stats for {self.user.username}"

    class Meta:
        verbose_name = 'User Statistics'
        verbose_name_plural = 'User Statistics'
