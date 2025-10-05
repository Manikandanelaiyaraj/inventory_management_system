from flask import Flask, render_template, request, redirect, url_for, flash
from models import db, Product, Location, ProductMovement
from sqlalchemy import func
from flask import jsonify
import uuid
from datetime import datetime


app = Flask(__name__)
app.secret_key = "secret123"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///inventory.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
with app.app_context():
    db.create_all()

# ---------------- PRODUCTS ----------------
@app.route('/products')
def products():
    all_products = Product.query.order_by(Product.created_at.desc()).all()
    return render_template("products.html", products=all_products)

from sqlalchemy import func

@app.route('/products/add', methods=['POST'])
def add_product():
    name = request.form['name']
    description = request.form['description']

    # Get the max product_id number
    max_id = db.session.query(func.max(Product.product_id)).scalar()
    if max_id:
        # Extract the numeric part and increment
        next_id = f"P{int(max_id[1:]) + 1:03}"
    else:
        next_id = "P001"

    product = Product(product_id=next_id, name=name, description=description)
    db.session.add(product)
    db.session.commit()
    flash("Product added successfully!", "success")
    return redirect(url_for('products'))


@app.route('/products/edit/<product_id>', methods=['POST'])
def edit_product(product_id):
    product = Product.query.get(product_id)
    product.name = request.form['name']
    product.description = request.form['description']
    db.session.commit()
    flash("Product updated!", "success")
    return redirect(url_for('products'))

@app.route('/products/delete/<product_id>')
def delete_product(product_id):
    product = Product.query.get(product_id)
    db.session.delete(product)
    db.session.commit()
    flash("Product deleted!", "danger")
    return redirect(url_for('products'))

# ---------------- LOCATIONS ----------------
@app.route('/locations')
def locations():
    all_locations = Location.query.order_by(Location.created_at.desc()).all()
    return render_template("locations.html", locations=all_locations)

@app.route('/locations/add', methods=['POST'])
def add_location():
    name = request.form['name']
    address = request.form['address']
    count = Location.query.count()
    location_id = f"L{count+1:03}"
    location = Location(location_id=location_id, name=name, address=address)
    db.session.add(location)
    db.session.commit()
    flash("Location added successfully!", "success")
    return redirect(url_for('locations'))

@app.route('/locations/edit/<location_id>', methods=['POST'])
def edit_location(location_id):
    location = Location.query.get(location_id)
    location.name = request.form['name']
    location.address = request.form['address']
    db.session.commit()
    flash("Location updated!", "success")
    return redirect(url_for('locations'))

@app.route('/locations/delete/<location_id>')
def delete_location(location_id):
    location = Location.query.get(location_id)
    db.session.delete(location)
    db.session.commit()
    flash("Location deleted!", "danger")
    return redirect(url_for('locations'))

# ---------------- MOVEMENTS ----------------
@app.route('/movements')
def movements():
    all_movements = ProductMovement.query.order_by(ProductMovement.timestamp.desc()).all()
    products = Product.query.all()
    locations = Location.query.all()
    return render_template("movements.html", movements=all_movements, products=products, locations=locations)

@app.route('/movements/add', methods=['POST'])
def add_movement():
    product_id = request.form['product_id']
    from_location = request.form.get('from_location') or None
    to_location = request.form.get('to_location') or None
    qty = int(request.form['qty'])

    # Generate short sequential movement ID
    count = ProductMovement.query.count()
    movement_id = f"M{count+1:03}"  # M001, M002, M003, ...

    # Create movement
    movement = ProductMovement(
        movement_id=movement_id,
        product_id=product_id,
        from_location=from_location,
        to_location=to_location,
        qty=qty,
        timestamp=datetime.now()   # ensure timestamp is added
    )

    try:
        db.session.add(movement)
        db.session.commit()
        flash("Movement recorded!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error recording movement: {str(e)}", "danger")

    return redirect(url_for('movements'))

@app.route('/movements/delete/<movement_id>')
def delete_movement(movement_id):
    movement = ProductMovement.query.get(movement_id)
    if movement:
        db.session.delete(movement)
        db.session.commit()
        flash("Movement deleted!", "danger")
    return redirect(url_for('movements'))


# ---------------- REPORT ----------------
from sqlalchemy.orm import aliased

@app.route('/report')
def report():
    FromLocation = aliased(Location)
    ToLocation = aliased(Location)

    # Query all movements with proper joins and aliases
    movements = (
        db.session.query(
            ProductMovement.movement_id,
            Product.name.label("product_name"),
            FromLocation.name.label("from_location"),
            ToLocation.name.label("to_location"),
            ProductMovement.qty,
            ProductMovement.timestamp
        )
        .join(Product, Product.product_id == ProductMovement.product_id)
        .outerjoin(FromLocation, FromLocation.location_id == ProductMovement.from_location)
        .outerjoin(ToLocation, ToLocation.location_id == ProductMovement.to_location)
        .order_by(ProductMovement.timestamp.desc())
        .all()
    )

    # 🔹 Important: use `movements` here to match the HTML
    return render_template("report.html", movements=movements)

@app.route('/')
def home():
    return redirect(url_for('products'))


if __name__ == "__main__":
    app.run(debug=True)
