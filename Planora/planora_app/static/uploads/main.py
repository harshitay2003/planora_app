from odoo import http
from odoo.http import request

class SubscriptionController(http.Controller):

    @http.route('/subscription', type='http', auth='public', website=True)
    def subscription_form(self, **kwargs):
        return request.render('website_subscription.subscription_form_template')

    @http.route('/subscription/submit', type='http', auth='public', website=True, csrf=True, methods=['POST'])
    def submit_subscription(self, **kwargs):
        name = kwargs.get('name')
        email = kwargs.get('email')
        phone = kwargs.get('phone')
        message = kwargs.get('message')

        if name and email:
            request.env['crm.lead'].sudo().create({
                'name': name,
                'partner_name': name,
                'email_from': email,
                'phone': phone,
                'description': message,
            })
            return request.redirect('/subscription/thank-you')
        
        return request.redirect('/subscription')

    @http.route('/subscription/thank-you', type='http', auth='public', website=True)
    def subscription_thank_you(self, **kwargs):
        return request.render('website_subscription.subscription_thank_you_template')


    @http.route('/shop/products', type='http', auth="public", website=True)
    def product_page(self, **kwargs):
        products = request.env['product.template'].sudo().search([('is_published', '=', True)])
        return request.render("website_subscription.product_template", {"products": products})