import os
import time
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

load_dotenv()

def get_driver():
    """Configure et retourne le driver Chrome pour WSL."""
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36")
    
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)

def login(driver):
    """Gère la première étape de connexion (Email)."""
    url = os.getenv("APP_URL")
    email = os.getenv("USER_EMAIL")
    
    print(f"Navigation vers {url}...")
    driver.get(url)
    
    # wait for email field
    wait = WebDriverWait(driver, 15)
    email_field = wait.until(EC.presence_of_element_located((By.ID, "loginEmail")))
    
    # Injection JavaScript
    print("Saisie de l'email...")
    driver.execute_script("arguments[0].value = arguments[1];", email_field, email)
    driver.execute_script("arguments[0].dispatchEvent(new Event('input', { bubbles: true }));", email_field)
    
    time.sleep(1) # wait for button

    # click login
    login_button = driver.find_element(By.CLASS_NAME, "loginButton")
    driver.execute_script("arguments[0].click();", login_button)
    print("Bouton Login cliqué.")

def main():
    driver = get_driver()
    try:
        login(driver)
        
        # wait for password page
        time.sleep(5)
        print(f"Page actuelle : {driver.title}")
        
        # TODO : Prochaine étape : Saisie du mot de passe
        
    except Exception as e:
        print(f"❌ Une erreur est survenue : {e}")
    finally:
        driver.quit()
        print("Navigateur fermé.")

if __name__ == "__main__":
    main()