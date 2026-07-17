def notifications_non_lues(request):
    if not request.user.is_authenticated:
        return {'notifications_non_lues': 0}
    return {'notifications_non_lues': request.user.notifications.filter(lue=False).count()}
