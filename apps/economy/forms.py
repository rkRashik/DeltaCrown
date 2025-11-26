# apps/economy/forms.py
from django import forms
from django.core.exceptions import ValidationError

from .models import WithdrawalRequest, DeltaCrownWallet


class WithdrawalRequestForm(forms.ModelForm):
    """
    Form for creating withdrawal request.
    
    Validates:
    - Amount > 0
    - Amount <= available balance
    - Payment method configured
    - PIN verification (if enabled)
    """
    
    pin = forms.CharField(
        max_length=4,
        min_length=4,
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
            'placeholder': '****',
            'autocomplete': 'off',
        }),
        help_text='Enter your 4-digit PIN to confirm withdrawal',
        required=True
    )
    
    user_note = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
            'placeholder': 'Optional: Add a note about this withdrawal',
            'rows': 3,
        }),
        required=False,
        help_text='Optional note about this withdrawal'
    )
    
    class Meta:
        model = WithdrawalRequest
        fields = ['amount', 'payment_method', 'user_note']
        widgets = {
            'amount': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
                'placeholder': 'Enter amount',
                'min': 1,
            }),
            'payment_method': forms.Select(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.wallet = kwargs.pop('wallet', None)
        super().__init__(*args, **kwargs)
        
        if self.wallet:
            # Update amount field help text with available balance
            self.fields['amount'].help_text = f'Available: {self.wallet.available_balance} DC'
            
            # Filter payment methods to only show configured ones
            configured_methods = []
            if self.wallet.bkash_number:
                configured_methods.append(('bkash', 'bKash'))
            if self.wallet.nagad_number:
                configured_methods.append(('nagad', 'Nagad'))
            if self.wallet.rocket_number:
                configured_methods.append(('rocket', 'Rocket'))
            if self.wallet.bank_account_number:
                configured_methods.append(('bank', 'Bank Transfer'))
            
            if configured_methods:
                self.fields['payment_method'].choices = [('', 'Select Payment Method')] + configured_methods
            else:
                self.fields['payment_method'].help_text = 'Please add a payment method first'
    
    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        
        if amount <= 0:
            raise ValidationError('Amount must be greater than 0')
        
        if self.wallet:
            if amount > self.wallet.available_balance:
                raise ValidationError(
                    f'Insufficient balance. Available: {self.wallet.available_balance} DC'
                )
        
        return amount
    
    def clean_payment_method(self):
        method = self.cleaned_data.get('payment_method')
        
        if not method:
            raise ValidationError('Please select a payment method')
        
        if self.wallet:
            # Verify payment method is configured
            if method == 'bkash' and not self.wallet.bkash_number:
                raise ValidationError('bKash account not configured')
            elif method == 'nagad' and not self.wallet.nagad_number:
                raise ValidationError('Nagad account not configured')
            elif method == 'rocket' and not self.wallet.rocket_number:
                raise ValidationError('Rocket account not configured')
            elif method == 'bank' and not self.wallet.bank_account_number:
                raise ValidationError('Bank account not configured')
        
        return method
    
    def clean_pin(self):
        pin = self.cleaned_data.get('pin')
        
        if not pin:
            raise ValidationError('PIN is required')
        
        if len(pin) != 4:
            raise ValidationError('PIN must be 4 digits')
        
        if not pin.isdigit():
            raise ValidationError('PIN must contain only digits')
        
        if self.wallet:
            if not self.wallet.has_pin():
                raise ValidationError('PIN not configured. Please set up your PIN first.')
            
            if not self.wallet.check_pin(pin):
                raise ValidationError('Incorrect PIN')
        
        return pin
    
    def save(self, commit=True):
        """
        Save withdrawal request and lock pending balance.
        """
        withdrawal = super().save(commit=False)
        withdrawal.wallet = self.wallet
        
        # Get payment details based on method
        method = withdrawal.payment_method
        if method == 'bkash':
            withdrawal.payment_number = self.wallet.bkash_number
        elif method == 'nagad':
            withdrawal.payment_number = self.wallet.nagad_number
        elif method == 'rocket':
            withdrawal.payment_number = self.wallet.rocket_number
        elif method == 'bank':
            withdrawal.payment_number = self.wallet.bank_account_number
            withdrawal.payment_details = {
                'bank_name': self.wallet.bank_name,
                'bank_branch': self.wallet.bank_branch,
                'account_name': self.wallet.bank_account_name,
            }
        
        if commit:
            withdrawal.save()
            
            # Lock pending balance
            self.wallet.pending_balance += withdrawal.amount
            self.wallet.save(update_fields=['pending_balance', 'updated_at'])
        
        return withdrawal


class PaymentMethodForm(forms.ModelForm):
    """
    Form for managing payment methods.
    Allows users to add/update bKash, Nagad, Rocket, or Bank details.
    """
    
    class Meta:
        model = DeltaCrownWallet
        fields = [
            'bkash_number',
            'nagad_number',
            'rocket_number',
            'bank_account_name',
            'bank_account_number',
            'bank_name',
            'bank_branch',
        ]
        widgets = {
            'bkash_number': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-pink-500 focus:border-transparent',
                'placeholder': '01XXXXXXXXX',
                'maxlength': 15,
            }),
            'nagad_number': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent',
                'placeholder': '01XXXXXXXXX',
                'maxlength': 15,
            }),
            'rocket_number': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent',
                'placeholder': '01XXXXXXXXX',
                'maxlength': 15,
            }),
            'bank_account_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
                'placeholder': 'Account holder name',
            }),
            'bank_account_number': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
                'placeholder': 'Account number',
            }),
            'bank_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
                'placeholder': 'Bank name (e.g., Dutch Bangla Bank)',
            }),
            'bank_branch': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
                'placeholder': 'Branch name',
            }),
        }
        help_texts = {
            'bkash_number': 'Enter your bKash mobile number (11 digits)',
            'nagad_number': 'Enter your Nagad mobile number (11 digits)',
            'rocket_number': 'Enter your Rocket mobile number (11 digits)',
            'bank_account_name': 'Name as it appears on your bank account',
            'bank_account_number': 'Your bank account number',
            'bank_name': 'Name of your bank',
            'bank_branch': 'Branch where account was opened',
        }
    
    def clean_bkash_number(self):
        number = self.cleaned_data.get('bkash_number')
        if number:
            # Basic validation - should start with 01 and be 11 digits
            if not number.startswith('01'):
                raise ValidationError('bKash number must start with 01')
            if len(number) != 11:
                raise ValidationError('bKash number must be 11 digits')
            if not number.isdigit():
                raise ValidationError('bKash number must contain only digits')
        return number
    
    def clean_nagad_number(self):
        number = self.cleaned_data.get('nagad_number')
        if number:
            if not number.startswith('01'):
                raise ValidationError('Nagad number must start with 01')
            if len(number) != 11:
                raise ValidationError('Nagad number must be 11 digits')
            if not number.isdigit():
                raise ValidationError('Nagad number must contain only digits')
        return number
    
    def clean_rocket_number(self):
        number = self.cleaned_data.get('rocket_number')
        if number:
            if not number.startswith('01'):
                raise ValidationError('Rocket number must start with 01')
            if len(number) != 11:
                raise ValidationError('Rocket number must be 11 digits')
            if not number.isdigit():
                raise ValidationError('Rocket number must contain only digits')
        return number
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Validate bank fields - if one is filled, all should be filled
        bank_fields = [
            cleaned_data.get('bank_account_name'),
            cleaned_data.get('bank_account_number'),
            cleaned_data.get('bank_name'),
        ]
        
        if any(bank_fields) and not all(bank_fields):
            raise ValidationError(
                'If providing bank details, Account Name, Account Number, and Bank Name are all required'
            )
        
        return cleaned_data


class PINSetupForm(forms.Form):
    """
    Form for setting up 4-digit PIN.
    """
    
    pin = forms.CharField(
        max_length=4,
        min_length=4,
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
            'placeholder': '****',
            'autocomplete': 'new-password',
        }),
        help_text='Enter a 4-digit PIN (numbers only)',
        label='New PIN'
    )
    
    pin_confirm = forms.CharField(
        max_length=4,
        min_length=4,
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
            'placeholder': '****',
            'autocomplete': 'new-password',
        }),
        help_text='Re-enter the same 4-digit PIN',
        label='Confirm PIN'
    )
    
    def clean_pin(self):
        pin = self.cleaned_data.get('pin')
        
        if not pin:
            raise ValidationError('PIN is required')
        
        if len(pin) != 4:
            raise ValidationError('PIN must be exactly 4 digits')
        
        if not pin.isdigit():
            raise ValidationError('PIN must contain only numbers')
        
        # Check for weak PINs
        if pin in ['0000', '1111', '2222', '3333', '4444', '5555', '6666', '7777', '8888', '9999']:
            raise ValidationError('PIN is too weak. Please choose a different PIN.')
        
        if pin in ['1234', '4321', '0123', '3210']:
            raise ValidationError('PIN is too common. Please choose a different PIN.')
        
        return pin
    
    def clean(self):
        cleaned_data = super().clean()
        pin = cleaned_data.get('pin')
        pin_confirm = cleaned_data.get('pin_confirm')
        
        if pin and pin_confirm and pin != pin_confirm:
            raise ValidationError('PINs do not match')
        
        return cleaned_data
