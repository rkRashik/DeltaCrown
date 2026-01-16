"""
KYC (Know Your Customer) Verification Views
Handles document upload, verification status, and admin review.
"""
import logging
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.db import transaction

from apps.user_profile.models_main import UserProfile, KYCSubmission

logger = logging.getLogger(__name__)


@login_required
@require_http_methods(["GET", "POST"])
def kyc_upload_view(request):
    """
    KYC document upload page.
    GET: Display upload form
    POST: Handle document upload
    """
    user_profile = UserProfile.objects.get(user=request.user)
    
    if request.method == "GET":
        # Get the latest submission if any
        latest_submission = user_profile.kyc_submissions.first()
        
        context = {
            'latest_submission': latest_submission,
            'user_profile': user_profile,
            'can_submit': user_profile.kyc_status in ['unverified', 'rejected'],
        }
        return render(request, 'user_profile/kyc/upload.html', context)
    
    # POST: Handle document upload
    try:
        document_type = request.POST.get('document_type')
        document_front = request.FILES.get('document_front')
        document_back = request.FILES.get('document_back')
        selfie_with_document = request.FILES.get('selfie_with_document')
        
        # Validation
        if not document_type:
            return JsonResponse({
                'success': False,
                'error': 'Document type is required'
            }, status=400)
        
        if not document_front:
            return JsonResponse({
                'success': False,
                'error': 'Front side of document is required'
            }, status=400)
        
        # Check file sizes (max 5MB each)
        max_size = 5 * 1024 * 1024  # 5MB
        if document_front.size > max_size:
            return JsonResponse({
                'success': False,
                'error': 'Document front image too large (max 5MB)'
            }, status=400)
        
        if document_back and document_back.size > max_size:
            return JsonResponse({
                'success': False,
                'error': 'Document back image too large (max 5MB)'
            }, status=400)
        
        if selfie_with_document and selfie_with_document.size > max_size:
            return JsonResponse({
                'success': False,
                'error': 'Selfie image too large (max 5MB)'
            }, status=400)
        
        with transaction.atomic():
            # Create new submission
            submission = KYCSubmission.objects.create(
                user_profile=user_profile,
                document_type=document_type,
                document_front=document_front,
                document_back=document_back,
                selfie_with_document=selfie_with_document,
                status='pending'
            )
            
            # Update user profile KYC status
            user_profile.kyc_status = 'pending'
            user_profile.save(update_fields=['kyc_status'])
            
            logger.info(f"[KYC-UPLOAD] User {request.user.username} submitted KYC documents (type: {document_type})")
            
            return JsonResponse({
                'success': True,
                'message': 'KYC documents uploaded successfully. Review typically takes 24-48 hours.',
                'submission_id': submission.id,
                'status': 'pending'
            })
    
    except Exception as e:
        logger.error(f"[KYC-UPLOAD-ERROR] User {request.user.username}: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'Failed to upload documents. Please try again.'
        }, status=500)


@login_required
@require_http_methods(["GET"])
def kyc_status_api(request):
    """
    API endpoint to get current KYC verification status.
    Used by frontend to display KYC status dynamically.
    """
    try:
        user_profile = UserProfile.objects.get(user=request.user)
        latest_submission = user_profile.kyc_submissions.first()
        
        response_data = {
            'success': True,
            'status': user_profile.kyc_status,
            'is_verified': user_profile.kyc_status == 'verified',
        }
        
        if latest_submission:
            response_data['submission_id'] = latest_submission.id
            response_data['document_type'] = latest_submission.document_type
            response_data['submitted_at'] = latest_submission.submitted_at.isoformat()
            
            if latest_submission.status == 'rejected':
                response_data['rejection_reason'] = latest_submission.rejection_reason
            
            if latest_submission.reviewed_at:
                response_data['reviewed_at'] = latest_submission.reviewed_at.isoformat()
        
        return JsonResponse(response_data)
    
    except UserProfile.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'User profile not found'
        }, status=404)
    except Exception as e:
        logger.error(f"[KYC-STATUS-ERROR] User {request.user.username}: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'Failed to fetch KYC status'
        }, status=500)


@login_required
@require_http_methods(["POST"])
def kyc_resubmit(request, submission_id):
    """
    Resubmit a rejected KYC submission with new documents.
    """
    try:
        user_profile = UserProfile.objects.get(user=request.user)
        old_submission = KYCSubmission.objects.get(id=submission_id, user_profile=user_profile)
        
        if old_submission.status != 'rejected':
            return JsonResponse({
                'success': False,
                'error': 'Can only resubmit rejected submissions'
            }, status=400)
        
        # Same validation as initial upload
        document_type = request.POST.get('document_type')
        document_front = request.FILES.get('document_front')
        document_back = request.FILES.get('document_back')
        selfie_with_document = request.FILES.get('selfie_with_document')
        
        if not document_front:
            return JsonResponse({
                'success': False,
                'error': 'Front side of document is required'
            }, status=400)
        
        with transaction.atomic():
            # Create new submission
            new_submission = KYCSubmission.objects.create(
                user_profile=user_profile,
                document_type=document_type or old_submission.document_type,
                document_front=document_front,
                document_back=document_back,
                selfie_with_document=selfie_with_document,
                status='pending'
            )
            
            # Update user profile KYC status
            user_profile.kyc_status = 'pending'
            user_profile.save(update_fields=['kyc_status'])
            
            logger.info(f"[KYC-RESUBMIT] User {request.user.username} resubmitted KYC (old: {submission_id}, new: {new_submission.id})")
            
            return JsonResponse({
                'success': True,
                'message': 'KYC documents resubmitted successfully.',
                'submission_id': new_submission.id
            })
    
    except KYCSubmission.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Submission not found'
        }, status=404)
    except Exception as e:
        logger.error(f"[KYC-RESUBMIT-ERROR] User {request.user.username}: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'Failed to resubmit documents'
        }, status=500)
