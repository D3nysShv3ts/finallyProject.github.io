from dotenv import load_dotenv
load_dotenv()

from online_restaurant import app

if __name__ == "__main__":
    from online_restaurant_db import init_database
    init_database()
    app.run(debug=True)
