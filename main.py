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
    """Configure le driver avec un profil persistant via le .env."""
    options = Options()
    
    # Récupération du chemin depuis le .env
    relative_profile_path = os.getenv("CHROME_PROFILE_PATH", "./.chrome_profile")
    # Conversion en chemin absolu (obligatoire pour Chrome)
    absolute_profile_path = os.path.abspath(relative_profile_path)
    
    options.add_argument(f"--user-data-dir={absolute_profile_path}")
    
    # Note : Pour la première connexion, le headless doit être désactivé
    options.add_argument("--headless") 
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
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

def handle_microsoft_login(driver):
    """Gère la saisie du mot de passe sur la page Microsoft."""
    password = os.getenv("USER_PASSWORD")
    wait = WebDriverWait(driver, 15)
    
    print("Étape Microsoft : Saisie du mot de passe...")
    
    # Attendre que le champ mot de passe soit visible et cliquable
    password_field = wait.until(EC.element_to_be_clickable((By.ID, "i0118")))
    
    # Saisie du mot de passe
    password_field.send_keys(password)
    
    # Attendre un court instant et cliquer sur le bouton "Se connecter" (idSIButton9)
    login_button = wait.until(EC.element_to_be_clickable((By.ID, "idSIButton9")))
    login_button.click()
    print("Bouton de connexion Microsoft cliqué.")

def clear_welcome_popups(driver):
    """Ferme la modale avec des sélecteurs simplifiés et robustes."""
    print("Vérification de la modale d'accueil...")
    wait = WebDriverWait(driver, 10)
    
    # Sélecteurs simplifiés basés sur tes classes
    ok_selector = "div.confirmation-wrapper button"
    close_selector = "div.close-card span"

    try:
        # On attend que la modale soit vraiment là (la div parente)
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "modal-card")))
        
        # On essaie de cliquer sur OK en priorité
        btn = driver.find_element(By.CSS_SELECTOR, ok_selector)
        driver.execute_script("arguments[0].click();", btn)
        print("✅ Modale fermée via 'Ok'.")
    except Exception:
        try:
            btn = driver.find_element(By.CSS_SELECTOR, close_selector)
            driver.execute_script("arguments[0].click();", btn)
            print("✅ Modale fermée via 'Close'.")
        except:
            print("Info : Pas de modale détectée.")

def main():
    driver = get_driver()
    try:
        driver.get(os.getenv("APP_URL"))
        time.sleep(3) # On laisse le temps au JS de charger la session
        
        # 1. On nettoie les pop-ups direct
        clear_welcome_popups(driver)
        
        # 2. On vérifie si on doit se logger (seulement si le champ est là)
        try:
            email_field = driver.find_element(By.ID, "loginEmail")
            if email_field.is_displayed():
                login(driver)
                handle_microsoft_login(driver)
                time.sleep(5)
                clear_welcome_popups(driver) # On re-vérifie après login
        except:
            print("Déjà connecté ou champ login absent.")

        print(f"🎉 État final - Titre : {driver.title}")
        driver.save_screenshot("dashboard_check.png")
        
    except Exception as e:
        print(f"❌ Erreur critique : {e}")
        driver.save_screenshot("error_debug.png")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()