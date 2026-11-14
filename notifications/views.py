from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .models import Notification


@login_required
def liste(request):
    page = Paginator(request.user.notifications.all(), 20).get_page(request.GET.get('page'))
    return render(request, 'notifications/liste.html', {'notifications': page, 'page_obj': page})


@login_required
@require_POST
def marquer_lue(request, pk):
    get_object_or_404(Notification, pk=pk, client=request.user).marquer_lue()
    return redirect(request.POST.get('next') or 'notifications:liste')
