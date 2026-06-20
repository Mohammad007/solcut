"""Demo data seeder. Run with:  flask --app run.py seed   (or python -m app.seed)

Re-running is safe: existing providers (matched by phone) are updated in place so
category/rating changes take effect without wiping bookings or loyalty cards.
"""
from app.extensions import db
from app.models.user import User
from app.models.provider import Provider
from app.models.barber import Barber
from app.models.service import Service

# Only two categories are supported: SALOON and PARLOUR.
# Coordinates are real-ish Indore (MP) points within ~5km of the city centre
# (22.7196, 75.8577) so /nearby returns a good spread.
SALOON_SERVICES = [
    ('Hair Cut', 'बाल कटिंग', 'HAIR', 120, 30),
    ('Beard Trim', 'दाढ़ी', 'BEARD', 60, 15),
    ('Hair Color', 'हेयर कलर', 'HAIR', 800, 60),
    ('Head Massage', 'सिर मालिश', 'HAIR', 150, 20),
]
PARLOUR_SERVICES = [
    ('Threading', 'थ्रेडिंग', 'THREADING', 40, 10),
    ('Facial', 'फेशियल', 'FACIAL', 600, 45),
    ('Waxing (Full Arm)', 'वैक्सिंग', 'WAXING', 300, 30),
    ('Manicure', 'मैनीक्योर', 'NAIL', 400, 40),
]

PROVIDERS = [
    {
        'phone': '9000000001', 'owner_name': 'Raju Sharma', 'shop_name': "Raju's Style Saloon",
        'shop_type': 'SALOON', 'mohalla': 'Vijay Nagar', 'city': 'Indore', 'state': 'Madhya Pradesh',
        'lat': 22.7533, 'lng': 75.8937, 'is_open': True, 'is_verified': True, 'is_premium': True,
        'rating': 4.8, 'rating_count': 214,
        'services': SALOON_SERVICES,
        'barbers': [('Raju', 'Classic cuts'), ('Imran', 'Fades & beard')],
    },
    {
        'phone': '9000000002', 'owner_name': 'Pooja Verma', 'shop_name': 'Glamour Ladies Parlour',
        'shop_type': 'PARLOUR', 'mohalla': 'Palasia', 'city': 'Indore', 'state': 'Madhya Pradesh',
        'lat': 22.7244, 'lng': 75.8839, 'is_open': True, 'is_verified': True, 'is_premium': True,
        'is_home_visit': True, 'home_visit_charge': 200, 'rating': 4.9, 'rating_count': 318,
        'services': PARLOUR_SERVICES,
        'barbers': [('Pooja', 'Bridal makeup'), ('Anjali', 'Skin & facials')],
    },
    {
        'phone': '9000000003', 'owner_name': 'Sameer Khan', 'shop_name': 'Urban Cuts Saloon',
        'shop_type': 'SALOON', 'mohalla': 'Bhawarkua', 'city': 'Indore', 'state': 'Madhya Pradesh',
        'lat': 22.6889, 'lng': 75.8666, 'is_open': False, 'is_verified': True,
        'rating': 4.5, 'rating_count': 96,
        'services': SALOON_SERVICES,
        'barbers': [('Sameer', 'Hair styling')],
    },
    {
        'phone': '9000000004', 'owner_name': 'Neha Joshi', 'shop_name': 'Blush Beauty Parlour',
        'shop_type': 'PARLOUR', 'mohalla': 'New Palasia', 'city': 'Indore', 'state': 'Madhya Pradesh',
        'lat': 22.7196, 'lng': 75.8800, 'is_open': True, 'is_verified': True,
        'is_home_visit': True, 'home_visit_charge': 150, 'rating': 4.7, 'rating_count': 142,
        'services': PARLOUR_SERVICES,
        'barbers': [('Neha', 'Nails & spa'), ('Kavya', 'Threading expert')],
    },
    {
        'phone': '9000000005', 'owner_name': 'Arjun Patel', 'shop_name': 'The Gentlemen Saloon',
        'shop_type': 'SALOON', 'mohalla': 'Saket Nagar', 'city': 'Indore', 'state': 'Madhya Pradesh',
        'lat': 22.7100, 'lng': 75.8650, 'is_open': True, 'is_verified': True,
        'rating': 4.6, 'rating_count': 178,
        'services': SALOON_SERVICES,
        'barbers': [('Arjun', 'Beard sculpting'), ('Vikas', 'Kids cuts')],
    },
    {
        'phone': '9000000006', 'owner_name': 'Ritu Agarwal', 'shop_name': 'Lavanya Parlour & Spa',
        'shop_type': 'PARLOUR', 'mohalla': 'Sudama Nagar', 'city': 'Indore', 'state': 'Madhya Pradesh',
        'lat': 22.7050, 'lng': 75.8450, 'is_open': True, 'is_verified': False,
        'rating': 4.3, 'rating_count': 54,
        'services': PARLOUR_SERVICES,
        'barbers': [('Ritu', 'Facials & cleanup')],
    },
]


def _apply_spec(p, spec):
    p.owner_name = spec['owner_name']
    p.shop_name = spec['shop_name']
    p.shop_type = spec['shop_type']
    p.mohalla = spec['mohalla']
    p.city = spec['city']
    p.state = spec['state']
    p.address_line = f"{spec['mohalla']}, {spec['city']}"
    p.latitude = spec['lat']
    p.longitude = spec['lng']
    p.is_open = spec['is_open']
    p.is_verified = spec['is_verified']
    p.is_premium = spec.get('is_premium', False)
    p.is_home_visit = spec.get('is_home_visit', False)
    p.home_visit_charge = spec.get('home_visit_charge')
    p.profile_complete = True
    p.open_time = '09:00'
    p.close_time = '21:00'
    p.rating = spec['rating']
    p.rating_count = spec['rating_count']


def run_seed():
    db.create_all()

    if not User.query.filter_by(phone='9876543210').first():
        db.session.add(User(
            phone='9876543210', name='Test Customer', city='Indore',
            state='Madhya Pradesh', preferred_lang='en',
        ))

    for spec in PROVIDERS:
        p = Provider.query.filter_by(phone=spec['phone']).first()
        is_new = p is None
        if is_new:
            p = Provider(phone=spec['phone'])
            db.session.add(p)
        _apply_spec(p, spec)
        db.session.flush()

        # Only seed services/barbers for brand-new providers.
        if is_new:
            for name, hi, cat, price, dur in spec['services']:
                db.session.add(Service(
                    provider_id=p.id, name=name, name_hindi=hi, category=cat,
                    price=price, duration_min=dur,
                ))
            for bname, spec_text in spec['barbers']:
                db.session.add(
                    Barber(provider_id=p.id, name=bname, speciality=spec_text, rating=4.6))

    db.session.commit()
    print(f'Seeded/updated {len(PROVIDERS)} providers (Saloon & Parlour) + demo customer.')
    print('Login OTP in mock mode is always 123456.')


if __name__ == '__main__':
    from app import create_app
    app = create_app()
    with app.app_context():
        run_seed()
