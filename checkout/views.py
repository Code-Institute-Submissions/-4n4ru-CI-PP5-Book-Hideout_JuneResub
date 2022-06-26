# Imports:
# 3rd party:
from django.shortcuts import render, reverse, redirect, get_object_or_404,\
    HttpResponse
from django.views.decorators.http import require_POST
from django.utils.decorators import method_decorator
from django.views import View
from django.contrib import messages
from django.conf import settings
import stripe
import json
from django.db.models import Q
from datetime import date


# Internal:
from bag.contexts import bag_contents
from products.models import Product
from profiles.forms import UserProfileForm
from profiles.models import UserProfile
from .models import OrderLineItem, Order
from .forms import OrderForm
from sale.models import Sale


@method_decorator(require_POST, name='dispatch')
class CacheCheckoutData(View):
    """A view to cache checkout data for the user, requires a POST method

    Args:
        View (class): Built in parent class for views
    """
    def post(self, request):
        """Cache checkout data for the user

        Args:
            request (object): request object

        Returns:
            HttpResponse
        """
        try:
            pid = request.POST.get('client_secret').split('_secret')[0]
            stripe.api_key = settings.STRIPE_SECRET_KEY
            stripe.PaymentIntent.modify(pid, metadata={
                'bag': json.dumps(request.session.get('bag', {})),
                'save_info': request.POST.get('save_info'),
                'username': request.user,
            })
            return HttpResponse(status=200)
        except Exception as e:
            messages.error(request, 'Sorry, your payment cannot be \
                processed right now. Please try again later.')
            return HttpResponse(content=e, status=400)


class Checkout(View):
    """A view to display the checkout page

    Args:
        View (class): Built in parent class for views
    """
    def get(self, request):
        """Renders the checkout page

        Args:
            request (object): HTTP request object

        Returns:
            method: renders checkout page
        """
        stripe_public_key = settings.STRIPE_PUBLIC_KEY
        stripe_secret_key = settings.STRIPE_SECRET_KEY

        bag = request.session.get('bag', {})
        if not bag:
            messages.error(
                request,
                "There's nothing in your bag at the moment"
            )
            return redirect(reverse('products'))
        current_bag = bag_contents(request)
        total = current_bag['grand_total']
        stripe_total = round(total * 100)
        stripe.api_key = stripe_secret_key
        intent = stripe.PaymentIntent.create(
            amount=stripe_total,
            currency=settings.STRIPE_CURRENCY,
        )

        if request.user.is_authenticated:
            try:
                profile = UserProfile.objects.get(user=request.user)
                order_form = OrderForm(initial={
                    'full_name': profile.user.get_full_name(),
                    'email': profile.user.email,
                    'phone_number': profile.default_phone_number,
                    'country': profile.default_country,
                    'postcode': profile.default_postcode,
                    'town_or_city': profile.default_town_or_city,
                    'street_address1': profile.default_street_address1,
                    'street_address2': profile.default_street_address2,
                    'county': profile.default_county,
                })
            except UserProfile.DoesNotExist:
                order_form = OrderForm()
        else:
            order_form = OrderForm()

        if not stripe_public_key:
            messages.warning(
                request,
                'Stripe public key is missing. \
                Did you forget to set it in your environment?'
            )

        template = 'checkout/checkout.html'
        context = {
            'order_form': order_form,
            'stripe_public_key': stripe_public_key,
            'client_secret': intent.client_secret,
        }

        return render(request, template, context)

    def post(self, request):
        """Handle the checkout form post request,
        if the form was valid render the
        checkout_success view, if there is an item in the page
        that doesn't exist return to the bag page.

        Args:
            request (object): HTTP request object

        Returns:
            method: render checkout_success page
        """
        bag = request.session.get('bag', {})
        form_data = {
            'full_name': request.POST['full_name'],
            'email': request.POST['email'],
            'phone_number': request.POST['phone_number'],
            'country': request.POST['country'],
            'postcode': request.POST['postcode'],
            'town_or_city': request.POST['town_or_city'],
            'street_address1': request.POST['street_address1'],
            'street_address2': request.POST['street_address2'],
            'county': request.POST['county'],
        }
        order_form = OrderForm(form_data)
        if order_form.is_valid():
            order = order_form.save(commit=False)
            pid = request.POST.get('client_secret').split('_secret')[0]
            order.stripe_pid = pid
            order.original_bag = json.dumps(bag)
            order.save()
            for item_id, quantity in bag.items():
                try:
                    product = Product.objects.get(id=item_id[0])
                    sales = Sale.objects.filter(
                        Q(start_date__lte=date.today())
                        & Q(end_date__gte=date.today())
                    )
                    if sales:
                        sale = sales.first()
                        for book in sale.books.all():
                            if product.id == book.id:
                                product.price = self.sale_price(sale.percentage, product.price)
                    order_line_item = OrderLineItem(
                        order=order,
                        product=product,
                        quantity=quantity,
                    )
                    order_line_item.save()
                except Product.DoesNotExist:
                    messages.error(
                        request,
                        "One of the products in your basket wasn't found \
                        in our database. Please call us for assistance!"
                    )
                    order.delete()
                    return redirect(reverse('bag'))
            request.session['save_info'] = 'save_info' in request.POST
            return redirect(reverse(
                'checkout_success',
                args=[order.order_number]
            ))
        else:
            messages.error(
                request,
                'There was an error with your form.\
                Please double check your information.'
            )

    def sale_price(self, percentage, price):
        return price * (100 - percentage ) / 100


class CheckoutSuccess(View):
    """A view to display the checkout success page

    Args:
        View (class): Built in parent class for views
    """
    def get(self, request, order_number):
        """
        Handle successful checkouts
        """
        save_info = request.session.get('save_info')
        order = get_object_or_404(Order, order_number=order_number)

        if request.user.is_authenticated:
            profile = UserProfile.objects.get(user=request.user)
            # Attach the user's profile to the order
            order.user_profile = profile
            order.save()

            # Save the user's info
            if save_info:
                profile_data = {
                    'default_phone_number': order.phone_number,
                    'default_country': order.country,
                    'default_postcode': order.postcode,
                    'default_town_or_city': order.town_or_city,
                    'default_street_address1': order.street_address1,
                    'default_street_address2': order.street_address2,
                    'default_county': order.county,
                }
                user_profile_form = UserProfileForm(
                    profile_data,
                    instance=profile
                )
                if user_profile_form.is_valid():
                    user_profile_form.save()

        messages.success(
            request,
            f'Order successfully processed! \
            Your order number is {order_number}. A confirmation \
            email will be sent to {order.email}.'
        )

        if 'bag' in request.session:
            del request.session['bag']

        template = 'checkout/checkout_success.html'
        context = {
            'order': order,
        }

        return render(request, template, context)
