from django.core.management.base import BaseCommand
import json
from comparer.models import FieldMapping

class Command(BaseCommand):
    help = 'Initialize common field mappings'

    def handle(self, *args, **kwargs):
        initial_mappings = {
            'transactionid': [
                'transactionid', 'id', 'transaction_id', 'trans_id', 'tid',
                'reference', 'ref_no', 'reference_number'
            ],
            'account': [
                'account', 'accountid', 'account_id', 'account_number',
                'acct_num', 'act_number'
            ],
            'date': [
                'date', 'transaction_date', 'trans_date', 'value_date',
                'posting_date', 'transactiondate'
            ],
            'amount': [
                'amount', 'transaction_amount', 'transactionamount',
                'value', 'total', 'sum'
            ],
            'type': [
                'type', 'transaction_type', 'transactiontype',
                'entry_type', 'tran_type'
            ],
            'description': [
                'description', 'desc', 'narrative', 'transaction_description',
                'details', 'particulars'
            ]
        }

        for field_type, variations in initial_mappings.items():
            mapping, created = FieldMapping.objects.get_or_create(
                field_type=field_type,
                defaults={
                    'variations': json.dumps(variations),
                    'description': f'Common variations for {field_type} field'
                }
            )
            
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created mapping for {field_type}'))
            else:
                # Update existing mapping with any new variations
                current_variations = set(mapping.get_variations())
                new_variations = set(variations)
                added_variations = new_variations - current_variations
                
                if added_variations:
                    for variation in added_variations:
                        mapping.add_variation(variation)
                    self.stdout.write(self.style.SUCCESS(
                        f'Updated mapping for {field_type} with {len(added_variations)} new variations'
                    ))
                else:
                    self.stdout.write(self.style.SUCCESS(
                        f'Mapping for {field_type} already up to date'
                    ))
