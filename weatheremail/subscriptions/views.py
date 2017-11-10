import datetime
import logging
import yarl

import django

from django.shortcuts import render
from subscriptions import forms, models, util


logger = logging.getLogger('__name__')
newsletters = {v: k for k, v in util.NEWSLETTERS_MAP.items()}


def normalize(log_message):
    return '%s "%s"' % (
        datetime.datetime.today().strftime('[%d/%b/%Y %H:%M:%S]'),
        log_message,)


def subscribe_we(request):
    '''
    Subscription Form Page for Weather Discount
    '''
    #  process the form data for POST
    if request.method == 'POST':
        # create a form instance and populate it with data from the request:
        form = forms.SubscriptionForm(request.POST)
        # check whether it's valid:
        if form.is_valid():
            # process the data in form.cleaned_data as required
            city = models.City.objects.get(id=form.cleaned_data['city'])
            try:
                subscriber, updated = models.Subscription.subscribe(
                    email=form.cleaned_data['email'],
                    newsletter=util.NEWSLETTERS_MAP['WEATHER DISCOUNT'],
                    city=city,
                )
                log_message = '<%s>, WD, %s: Subscribed: updated: %s' % (
                    subscriber.email, subscriber.city, updated)
                logger.warning(normalize(log_message))
                data = {
                    'updated': updated,
                    'email': subscriber.email,
                    'newsletter': newsletters[subscriber.newsletter].title(),
                    'city': str(subscriber.city),
                }
                html = django.template.loader.render_to_string(
                    'thanks_email.html',
                    data,
                )
                subject = {
                    True: 'Thanks for updating you subscription.',
                    False: 'Thanks for subcribing.',
                }
                email = django.core.mail.EmailMessage(
                    subject=subject[updated],
                    body=html,
                    from_email=django.conf.settings.DEFAULT_FROM_EMAIL,
                    to=[subscriber.email],
                )
                email.content_subtype = 'html'
                email.send()
                log_message = 'Email sent to <%s>' % (subscriber.email)
                logger.warning(normalize(log_message))
                # redirect to a new URL:
                params = {
                    'updated': str(updated),
                    'id': subscriber.id,
                }
                # use yarl to create query strings to pass to redirected page
                return django.http.HttpResponseRedirect(
                    yarl.URL('thanks').with_query(params)
                )
            except django.db.IntegrityError:
                log_message = '<%s>, WD, %s: Resubscription attempt' % (
                    form.cleaned_data['email'], city)
                logger.error(normalize(log_message))
                # Duplicate error with valid form. Show message to user.
                django.contrib.messages.error(
                    request,
                    ('Email <i>%s</i> is already subscribed to '
                    '<b>Weather Discount</b> for %s. If you have moved, you '
                    'can update the city.') % (
                        form.cleaned_data['email'], city),
                    extra_tags='safe'
                )
    # create a blank form for GET (or any other method)
    else:
        form = forms.SubscriptionForm()
    return render(
        request,
        'subscription.html',
        {'form': form}
    )


def thanks(request):
    '''
    Thank You Page.
    '''
    subscription = models.Subscription.objects.get(id=request.GET.get('id'))
    data = {
        'updated': request.GET.get('updated'),
        'email': subscription.email,
        'newsletter': newsletters[subscription.newsletter].title(),
        'city': str(subscription.city),
    }
    return render(request, 'thanks.html', data)
