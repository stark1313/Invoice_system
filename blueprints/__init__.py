def register_blueprints(app):
    from .main import bp as main_bp
    from .company import bp as company_bp
    from .documents import bp as documents_bp
    from .customers import bp as customers_bp
    from .items import bp as items_bp
    from .transactions import bp as transactions_bp
    from .printing import bp as printing_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(company_bp)
    app.register_blueprint(documents_bp)
    app.register_blueprint(customers_bp)
    app.register_blueprint(items_bp)
    app.register_blueprint(transactions_bp)
    app.register_blueprint(printing_bp)
