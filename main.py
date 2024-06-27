from app_folder import create_app

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)