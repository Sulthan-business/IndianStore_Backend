from django.core.mail import send_mail

def email_order_placed(order):
    subj = f"Order #{order.id} placed"
    send_mail(subj, f"Thanks! Total: {order.total_price}", None, [order.user.email or "dev@example.local"])

def email_order_shipped(order):
    subj = f"Order #{order.id} shipped"
    send_mail(subj, f"Tracking: {order.tracking_no or 'TBA'}", None, [order.user.email or "dev@example.local"])
