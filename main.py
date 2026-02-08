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

def close_modal_via_cross(driver):
    """
    Ferme n'importe quelle modale (Accueil ou Confirmation) en cliquant sur la croix.
    Sélecteur basé sur : #root > div > div.modal-card.show > div > div.close-card > span
    """
    print("Vérification de présence d'une modale à fermer...")
    wait = WebDriverWait(driver, 5)
    
    # Sélecteur CSS précis dérivé de ta structure HTML
    cross_selector = "div.modal-card.show div.close-card > span"

    try:
        # On attend que la croix soit cliquable
        cross_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, cross_selector)))
        driver.execute_script("arguments[0].click();", cross_btn)
        print("✅ Modale fermée via la croix.")
    except Exception:
        print("Info : Pas de croix de modale détectée (ou déjà fermée).")

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
        seat_locator = f"//p[@class='favorites-card-name' and contains(text(), '{preferred_seat}')]"
        seat_element = wait.until(EC.element_to_be_clickable((By.XPATH, seat_locator)))
        
        # On clique sur le bureau pour ouvrir le menu d'options
        driver.execute_script("arguments[0].click();", seat_element)
        print(f"✅ Bureau '{preferred_seat}' trouvé et sélectionné.")
        
        # 3. Cliquer sur "Book now" dans le menu qui vient de s'ouvrir
        time.sleep(1) # Petit temps pour l'animation du menu
        book_now_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "div.action-sheet-option:nth-child(1)")))
        
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
        # Utilisation du JSPath exact
        jspath_next = "#root > div > div.page-content > div > div.day-selection-wrapper > div.day-selection > div:nth-child(9)"
        
        # On force le clic via JS
        script = f"document.querySelector('{jspath_next}').click();"
        driver.execute_script(script)
        
        print(f"Clic navigation {i+1}/{weeks_to_advance}")
        time.sleep(2) 

    # 2. Sélection du jour
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
        raw_text = time_element.text.split('|')[-1].strip()
        clean_time = raw_text.replace('\xa0', ' ').strip()
        
        try:
            return datetime.strptime(clean_time, "%H:%M")
        except ValueError:
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

        # 2. Calcul du mouvement
        pixels_to_move = diff_minutes * 1 
        step_pixels = max(min(pixels_to_move, 200), -200)
        
        print(f"🔄 Itération {iteration} : Heure actuelle {current_time.strftime('%H:%M')}")
        print(f"👉 Déplacement de {step_pixels}px (Reste à faire : {pixels_to_move}px)")

        # 3. Action : Scroll + Drag
        try:
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", booking_block)
            time.sleep(1)

            actions = ActionChains(driver)
            actions.move_to_element(booking_block)
            actions.click_and_hold()
            actions.pause(0.3)
            actions.move_by_offset(0, step_pixels)
            actions.pause(0.5)
            actions.release()
            actions.perform()
            
            time.sleep(2) 
            # driver.save_screenshot(f"debug_step_{iteration}.png") # Debug optionnel
            
        except Exception as e:
            print(f"❌ Erreur lors du drag à l'itération {iteration} : {e}")
            break

    print(f"🏁 Ajustement terminé après {iteration} itérations.")

def confirm_booking(driver):
    """Enchaîne les étapes de validation finale."""
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
        
        print("⏳ Traitement de la réservation...")
        time.sleep(3)

        # --- ÉTAPE 3 : Fermeture de la pop-up via la fonction commune ---
        print("Étape 3/3 : Fermeture de la confirmation...")
        close_modal_via_cross(driver)
        
        print("✅ RÉSERVATION TERMINÉE AVEC SUCCÈS !")
        driver.save_screenshot("booking_final_success.png")

    except Exception as e:
        print(f"❌ Erreur lors de la confirmation finale : {e}")
        driver.save_screenshot("error_confirmation_steps.png")

def main():
    # 1. Paramètres
    target_date_input = input("Entrez la date de réservation (JJ/MM/AAAA) : ")
    start_time_env = os.getenv("START_TIME")
    
    if not start_time_env:
        print("❌ Erreur : START_TIME n'est pas défini dans le .env")
        return

    try:
        datetime.strptime(target_date_input, "%d/%m/%Y")
        target_h, target_m = map(int, start_time_env.split(":"))
    except ValueError:
        print("❌ Format de date ou d'heure invalide.")
        return

    # 2. Driver
    driver = get_driver()
    
    try:
        driver.get(os.getenv("APP_URL"))
        time.sleep(3)
        
        # 3. Nettoyage initial (Modale d'accueil)
        # On utilise la nouvelle fonction générique
        close_modal_via_cross(driver)
        
        # NOTE : L'authentification est gérée par le profil Chrome existant.
        # Si la session est expirée, le script échouera ici et demandera une connexion manuelle.

        # 4. Navigation favoris
        navigate_to_favorite(driver)
        time.sleep(2)

        # 5. Sélection date
        select_booking_date(driver, target_date_input)
        time.sleep(2)

        # 6. Ajustement heure
        adjust_booking_time(driver, target_hour=target_h, target_minute=target_m)
        
        # 7. Confirmation (Book -> Confirm -> Close)
        confirm_booking(driver)
        
        print(f"\n✨ PROCESSUS TERMINÉ pour le {target_date_input} à {start_time_env} !")

    except Exception as e:
        print(f"\n❌ Erreur critique : {e}")
        driver.save_screenshot("error_main_crash.png")
    finally:
        driver.quit()
        print("Navigateur fermé.")

if __name__ == "__main__":
    main()