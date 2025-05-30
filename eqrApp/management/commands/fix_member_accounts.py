from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from eqrApp.models import Member

class Command(BaseCommand):
    help = 'Fix member user accounts and passwords'

    def handle(self, *args, **options):
        members = Member.objects.all()
        fixed_count = 0
        created_count = 0
        
        for member in members:
            self.stdout.write(f"Processing member: {member.member_id} - {member.get_full_name()}")
            
            try:
                # Try to get existing user account
                user = User.objects.get(username=member.member_id)
                
                # Update the password to match the last name
                password = member.last_name.strip() if member.last_name.strip() else "TempPass123"
                user.set_password(password)
                user.first_name = member.first_name
                user.last_name = member.last_name
                user.email = member.email or ''
                user.is_active = True
                user.save()
                
                # Update member's temp_password field
                member.temp_password = password
                member.save(update_fields=['temp_password', 'password_generated_at'])
                
                self.stdout.write(
                    self.style.SUCCESS(f"✓ Fixed user account for {member.member_id} - Password: {password}")
                )
                fixed_count += 1
                
            except User.DoesNotExist:
                # Create new user account
                password = member.create_user_account()
                if password:
                    self.stdout.write(
                        self.style.SUCCESS(f"✓ Created user account for {member.member_id} - Password: {password}")
                    )
                    created_count += 1
                else:
                    self.stdout.write(
                        self.style.ERROR(f"✗ Failed to create user account for {member.member_id}")
                    )
            
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"✗ Error processing {member.member_id}: {e}")
                )
        
        self.stdout.write(
            self.style.SUCCESS(f"\nCompleted! Fixed: {fixed_count}, Created: {created_count}")
        )