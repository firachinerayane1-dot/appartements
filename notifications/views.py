from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .models import Notification


@login_required
def liste(request):
    return render(request, 'notifications/liste.html', {'notifications': request.user.notifications.all()})


@login_required
@require_POST
def marquer_lue(request, pk):
    get_object_or_404(Notification, pk=pk, client=request.user).marquer_lue()
    return redirect(request.POST.get('next') or 'notifications:liste')
