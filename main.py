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
from datetime import datetime
from selenium.webdriver import ActionChains

load_dotenv()

def get_driver():
    options = Options()
    # On garde ton profil
    relative_profile_path = os.getenv("CHROME_PROFILE_PATH", "./.chrome_profile")
    absolute_profile_path = os.path.abspath(relative_profile_path)
    options.add_argument(f"--user-data-dir={absolute_profile_path}")
    
    options.add_argument("--headless") 
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    # RÉSOLUTION : On force une hauteur de 2000px pour avoir de la place verticalement
    options.add_argument("--window-size=1920,2000")
    
    # On force un User-Agent Desktop pour essayer de "casser" le mode smartphone
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36")

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

def navigate_to_favorite(driver):
    """Ouvre la section favoris et clique sur le bureau préféré."""
    preferred_seat = os.getenv("PREFERRED_SEAT")
    wait = WebDriverWait(driver, 10)
    
    print(f"Recherche du bureau favori : {preferred_seat}...")
    
    try:
        # 1. Cliquer sur le header "My Favorites" pour s'assurer qu'il est déplié
        fav_header = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "favorites-header-wrapper")))
        driver.execute_script("arguments[0].click();", fav_header)
        
        # 2. Trouver le bureau par son nom (p.favorites-card-name)
        # On utilise un XPATH pour trouver le paragraphe qui contient exactement le texte du .env
        seat_locator = f"//p[@class='favorites-card-name' and contains(text(), '{preferred_seat}')]"
        seat_element = wait.until(EC.element_to_be_clickable((By.XPATH, seat_locator)))
        
        # On clique sur le bureau pour ouvrir le menu d'options
        driver.execute_script("arguments[0].click();", seat_element)
        print(f"✅ Bureau '{preferred_seat}' trouvé et sélectionné.")
        
        # 3. Cliquer sur "Book now" dans le menu qui vient de s'ouvrir
        # On utilise le sélecteur nth-child(1) comme tu l'as suggéré
        time.sleep(1) # Petit temps pour l'animation du menu
        book_now_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "div.action-sheet-option:nth-child(1)")))
        
        # On vérifie par sécurité que c'est le bon bouton
        if "book now" in book_now_btn.text.lower():
            driver.execute_script("arguments[0].click();", book_now_btn)
            print("✅ Bouton 'Book now' cliqué.")
        else:
            print(f"⚠️ Attention: Le premier bouton n'est pas 'Book now' mais '{book_now_btn.text}'")

    except Exception as e:
        print(f"❌ Erreur lors de la sélection du favori : {e}")
        driver.save_screenshot("error_favorite.png")
        raise e
    
def select_booking_date(driver, target_date_str):
    target_date = datetime.strptime(target_date_str, "%d/%m/%Y")
    today = datetime.now()
    wait = WebDriverWait(driver, 10)
    
    # 1. Calcul de l'écart de semaines
    current_week_number = today.isocalendar()[1]
    target_week_number = target_date.isocalendar()[1]
    
    # Correction pour l'année prochaine si nécessaire
    weeks_to_advance = target_week_number - current_week_number
    if target_date.year > today.year:
        weeks_to_advance += 52 

    print(f"Navigation : avance de {weeks_to_advance} semaine(s)...")
    
    for i in range(weeks_to_advance):
        # Utilisation du JSPath exact que tu as fourni
        jspath_next = "#root > div > div.page-content > div > div.day-selection-wrapper > div.day-selection > div:nth-child(9)"
        
        # On récupère l'élément via JavaScript et on clique dessus
        script = f"document.querySelector('{jspath_next}').click();"
        driver.execute_script(script)
        
        print(f"Clic navigation {i+1}/{weeks_to_advance}")
        time.sleep(2) # Vital pour laisser le calendrier se mettre à jour

    # 2. Sélection du jour via ton sélecteur nth-child
    day_index = target_date.weekday() + 2
    day_selector = f"div.day-item-wrapper:nth-child({day_index})"
    
    print(f"Sélection du jour : {target_date.strftime('%A')} (index {day_index})...")
    day_element = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, day_selector)))
    driver.execute_script("arguments[0].click();", day_element)
    
    # 3. Vérification finale
    time.sleep(2)
    selected_display = driver.find_element(By.CLASS_NAME, "selected-day").text
    if target_date_str in selected_display:
        print(f"✅ Date {target_date_str} correctement sélectionnée !")
    else:
        print(f"⚠️ Erreur : L'interface affiche toujours {selected_display}")

def get_current_booking_time(driver):
    """Récupère l'heure et gère les formats 24h ou AM/PM."""
    try:
        time_element = driver.find_element(By.CSS_SELECTOR, "span.entity-timeslot:nth-child(2)")
        # On récupère le texte, ex: "Thu 12/02/2026 | 04:45 PM" ou "12/02/2026 | 16:45"
        raw_text = time_element.text.split('|')[-1].strip()
        
        # Nettoyage des espaces bizarres (caractères non-breaking space, etc.)
        clean_time = raw_text.replace('\xa0', ' ').strip()
        
        try:
            # Tentative 1 : Format 24h (16:45)
            return datetime.strptime(clean_time, "%H:%M")
        except ValueError:
            # Tentative 2 : Format AM/PM (04:45 PM)
            # %I est l'heure sur 12h, %p est AM ou PM
            return datetime.strptime(clean_time, "%I:%M %p")
            
    except Exception as e:
        print(f"⚠️ Erreur de lecture heure ({raw_text}) : {e}")
        return None

def adjust_booking_time(driver, target_hour=8, target_minute=30):
    print(f"🎯 Cible : {target_hour:02d}:{target_minute:02d}")
    wait = WebDriverWait(driver, 10)
    
    target_total_min = (target_hour * 60) + target_minute
    iteration = 0

    while True:
        iteration += 1
        booking_block = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "new-booking-item")))
        
        # 1. Récupérer l'heure actuelle
        current_time = get_current_booking_time(driver)
        if not current_time: break
        
        current_total_min = (current_time.hour * 60) + current_time.minute
        diff_minutes = target_total_min - current_total_min
        
        # Si on est à moins de 2 minutes de la cible, on arrête
        if abs(diff_minutes) <= 2:
            print(f"✅ Heure cible atteinte : {current_time.strftime('%H:%M')}")
            break

        # 2. Calcul du mouvement pour cette itération (max 200px)
        # Ratio 60px/h -> 1px/min
        pixels_to_move = diff_minutes * 1 
        
        # On plafonne le mouvement à 200px (positif ou négatif)
        step_pixels = max(min(pixels_to_move, 200), -200)
        
        print(f"🔄 Itération {iteration} : Heure actuelle {current_time.strftime('%H:%M')}")
        print(f"👉 Déplacement de {step_pixels}px (Reste à faire : {pixels_to_move}px)")

        # 3. Action : Scroll + Drag
        try:
            # On s'assure que le bloc est bien en vue
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", booking_block)
            time.sleep(1)

            actions = ActionChains(driver)
            # On décompose bien : Pointer -> Cliquer -> Bouger -> Relâcher
            actions.move_to_element(booking_block)
            actions.click_and_hold()
            actions.pause(0.3)
            actions.move_by_offset(0, step_pixels)
            actions.pause(0.5)
            actions.release()
            actions.perform()
            
            # Attente de la mise à jour du DOM
            time.sleep(2) 
            driver.save_screenshot(f"debug_step_{iteration}.png")
            
        except Exception as e:
            print(f"❌ Erreur lors du drag à l'itération {iteration} : {e}")
            break

    print(f"🏁 Ajustement terminé après {iteration} itérations.")

def confirm_booking(driver):
    """Enchaîne les 3 étapes de validation finale."""
    print("🚀 Lancement de la procédure de confirmation...")
    wait = WebDriverWait(driver, 10)
    
    try:
        # --- ÉTAPE 1 : Bouton 'Book' ---
        print("Étape 1/3 : Clic sur 'Book'...")
        book_btn = wait.until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, "button.button.primary.full-width.regular-height")
        ))
        driver.execute_script("arguments[0].click();", book_btn)
        time.sleep(1.5)

        # --- ÉTAPE 2 : Bouton 'Confirm' ---
        print("Étape 2/3 : Clic sur 'Confirm'...")
        confirm_btn = wait.until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, "button.button.primary.half-width.regular-height")
        ))
        driver.execute_script("arguments[0].click();", confirm_btn)
        
        # On attend que la réservation soit enregistrée côté serveur
        print("⏳ Traitement de la réservation...")
        time.sleep(3)

        # --- ÉTAPE 3 : Fermeture de la pop-up de succès ---
        print("Étape 3/3 : Fermeture de la confirmation...")
        close_cross = wait.until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, "span.close")
        ))
        driver.execute_script("arguments[0].click();", close_cross)
        
        print("✅ RÉSERVATION TERMINÉE AVEC SUCCÈS !")
        driver.save_screenshot("booking_final_success.png")

    except Exception as e:
        print(f"❌ Erreur lors de la confirmation finale : {e}")
        driver.save_screenshot("error_confirmation_steps.png")

def main():
    # 1. Préparation et récupération des paramètres
    target_date_input = input("Entrez la date de réservation (JJ/MM/AAAA) : ")
    
    start_time_env = os.getenv("START_TIME")
    if not start_time_env:
        print("❌ Erreur : START_TIME n'est pas défini dans le .env (ex: START_TIME=08:30)")
        return

    try:
        # Validation du format date
        datetime.strptime(target_date_input, "%d/%m/%Y")
        # Extraction heure/minute cible
        target_h, target_m = map(int, start_time_env.split(":"))
    except ValueError:
        print("❌ Format de date ou d'heure invalide.")
        return

    # 2. Initialisation du Driver (avec résolution 1920x2000)
    driver = get_driver()
    
    try:
        driver.get(os.getenv("APP_URL"))
        time.sleep(3)
        
        # 3. Authentification et nettoyage
        clear_welcome_popups(driver)
        
        # Tentative de login si nécessaire
        if driver.find_elements(By.ID, "loginEmail"):
            login(driver)
            handle_microsoft_login(driver)
            time.sleep(5)
            clear_welcome_popups(driver)

        # 4. Navigation vers le bureau favori
        navigate_to_favorite(driver)
        time.sleep(2)

        # 5. Sélection de la date (Logique ISO Week)
        select_booking_date(driver, target_date_input)
        time.sleep(2)

        # 6. Ajustement itératif de l'heure (Drag & Drop pas à pas)
        # Cette fonction utilise get_current_booking_time avec gestion AM/PM
        adjust_booking_time(driver, target_hour=target_h, target_minute=target_m)
        
        # Capture de sécurité avant le clic final
        driver.save_screenshot("final_check_before_booking.png")
        print("📸 Vérification finale enregistrée.")

        # 7. Séquence de confirmation finale (Book -> Confirm -> Close)
        confirm_booking(driver)
        
        print(f"\n✨ PROCESSUS TERMINÉ AVEC SUCCÈS pour le {target_date_input} à {start_time_env} !")

    except Exception as e:
        print(f"\n❌ Une erreur critique est survenue durant le flux : {e}")
        driver.save_screenshot("error_main_crash.png")
    finally:
        # 8. Fermeture propre
        driver.quit()
        print("Navigateur fermé.")

if __name__ == "__main__":
    main()