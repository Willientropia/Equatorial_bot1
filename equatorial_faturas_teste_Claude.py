#!/usr/bin/env python3

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.support.ui import Select
import time
import os
import logging
from datetime import datetime
import json
import os
import requests



# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('equatorial_selenium.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)



def load_credentials_from_json():
        """Carrega as credenciais de um arquivo JSON"""
        json_path = "dados.json"
        if not os.path.exists(json_path):
            return None
            
        try:
            with open(json_path, 'r') as f:
                data = json.load(f)
                return {
                    "uc": data.get("uc", ""),
                    "cpf_cnpj": data.get("cpf_cnpj", ""),
                    "data_nascimento": data.get("data_nascimento", "")
                }
        except Exception as e:
            logger.error(f"Erro ao ler arquivo JSON: {e}")
            return None



class EquatorialDownloaderFixed:

#-------------- Passo 0 ---------#
    def __init__(self, headless=False):
        self.driver = None
        self.wait = None
        self.base_url = "https://goias.equatorialenergia.com.br"
        self.login_url = f"{self.base_url}/LoginGO.aspx"
        self.headless = headless
        self.logged_in = False
        self.step = 1  # Controla qual etapa do login estamos

    def setup_driver(self):
        """Configura e inicializa o driver do Chrome - VERSÃO ATUALIZADA"""
        try:
            chrome_options = Options()
            
            # Configurações do Chrome
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            
            # Modo headless opcional
            if self.headless:
                chrome_options.add_argument("--headless")
                logger.info("Executando em modo headless")
            else:
                logger.info("Executando em modo visual - navegador será aberto")
            
            # Configurações de download ATUALIZADAS
            # Nota: O diretório será alterado dinamicamente para cada cliente
            self.download_base_dir = os.path.abspath("clientes_faturas")
            os.makedirs(self.download_base_dir, exist_ok=True)
            
            prefs = {
                "download.default_directory": self.download_base_dir,
                "download.prompt_for_download": False,
                "download.directory_upgrade": True,
                "safebrowsing.enabled": True,
                "safebrowsing.disable_download_protection": True,
                "plugins.always_open_pdf_externally": True,
                "profile.default_content_setting_values.automatic_downloads": 1,
                "profile.default_content_settings.popups": 0
            }
            chrome_options.add_experimental_option("prefs", prefs)
            
            # Adiciona configurações para permitir múltiplos downloads
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-setuid-sandbox")
            
            # Inicializa o driver
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            # Habilita download em modo headless se necessário
            if self.headless:
                params = {
                    "behavior": "allow",
                    "downloadPath": self.download_base_dir
                }
                self.driver.execute_cdp_cmd("Page.setDownloadBehavior", params)
            
            # Configura timeout
            self.wait = WebDriverWait(self.driver, 15)
            logger.info("Driver do Chrome inicializado com sucesso")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao configurar driver: {e}")
            print("\n❌ ERRO: Não foi possível inicializar o Chrome WebDriver")
            print("📋 Soluções possíveis:")
            print("1. Instale o ChromeDriver: pip install chromedriver-autoinstaller")
            print("2. Ou baixe manualmente em: https://chromedriver.chromium.org/")
            print("3. Certifique-se que o Chrome está instalado")
            return False

    def update_download_folder_for_client(self, client_folder):
        """Atualiza a pasta de download para o cliente específico"""
        try:
            # Atualiza as preferências de download para a pasta do cliente
            params = {
                "behavior": "allow",
                "downloadPath": os.path.abspath(client_folder)
            }
            self.driver.execute_cdp_cmd("Page.setDownloadBehavior", params)
            print(f"📁 Pasta de download atualizada para: {client_folder}")
            return True
        except Exception as e:
            print(f"⚠️ Erro ao atualizar pasta de download: {e}")
            return False

    def open_login_page(self):
        """Abre a página de login"""
        try:
            logger.info("Abrindo página de login...")
            self.driver.get(self.login_url)
            
            # Aguarda a página carregar completamente
            self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "form")))
            time.sleep(2)  # Aguarda elementos JavaScript carregarem
            
            print(f"\n🌐 Página aberta: {self.driver.current_url}")
            print("👀 Você pode acompanhar o processo no navegador que foi aberto")
            return True
            
        except TimeoutException:
            logger.error("Timeout ao carregar página de login")
            return False
        except Exception as e:
            logger.error(f"Erro ao abrir página de login: {e}")
            return False


#-------------- Passo 1 ----------#
    def step1_fill_uc_cpf(self, uc, cpf_cnpj):
        """Etapa 1: Preenche UC e CPF/CNPJ"""
        try:
            print("\n📝 ETAPA 1: Preenchendo UC e CPF/CNPJ...")
            
            # Aguarda um pouco para garantir que a página carregou
            time.sleep(3)
            
            # PRIMEIRO: Vamos fazer um debug completo da página
            print("\n🔍 ANALISANDO PÁGINA ATUAL...")
            self.debug_page_elements()
            
            # Procura pelo campo UC - usando seletores do código original que funcionava
            print("\n🔍 Procurando campo UC...")
            uc_selectors = [
                "input[name*='UC' i]",
                "input[id*='UC' i]",
                "input[name*='unidade' i]",
                "input[id*='unidade' i]",
                "input[placeholder*='unidade' i]",
                "input[name*='txtUC']",
                "input[id*='txtUC']"
            ]
            
            uc_field = None
            for selector in uc_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    print(f"  Testando seletor: {selector} - Encontrados: {len(elements)}")
                    for i, element in enumerate(elements):
                        try:
                            displayed = element.is_displayed()
                            enabled = element.is_enabled()
                            name = element.get_attribute('name') or 'sem nome'
                            id_attr = element.get_attribute('id') or 'sem id'
                            print(f"    Elemento {i+1}: name='{name}' id='{id_attr}' displayed={displayed} enabled={enabled}")
                            
                            if displayed and enabled:
                                uc_field = element
                                logger.info(f"Campo UC encontrado com seletor: {selector}")
                                break
                        except Exception as inner_e:
                            print(f"    Erro ao verificar elemento {i+1}: {inner_e}")
                    if uc_field:
                        break
                except Exception as e:
                    print(f"  Erro com seletor {selector}: {e}")
                    continue
            
            if uc_field:
                # Limpa e preenche UC
                print("✅ Campo UC encontrado! Preenchendo...")
                uc_field.clear()
                time.sleep(0.5)
                uc_field.send_keys(uc)
                logger.info(f"UC preenchida: {uc}")
                
                # Destaca o campo
                self.driver.execute_script(
                    "arguments[0].style.backgroundColor='lightgreen';" +
                    "arguments[0].style.border='2px solid green';",
                    uc_field
                )
            else:
                print("❌ Campo UC não encontrado com nenhum seletor")
                return False
            
            # Procura pelo campo CPF/CNPJ - usando seletores do código original
            print("\n🔍 Procurando campo CPF/CNPJ...")
            cpf_selectors = [
                "input[name*='CPF' i]",
                "input[id*='CPF' i]",
                "input[name*='cnpj' i]",
                "input[id*='cnpj' i]",
                "input[name*='documento' i]",
                "input[placeholder*='cpf' i]",
                "input[name*='txtCPF']",
                "input[id*='txtCPF']"
            ]
            
            cpf_field = None
            for selector in cpf_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    print(f"  Testando seletor: {selector} - Encontrados: {len(elements)}")
                    for i, element in enumerate(elements):
                        try:
                            displayed = element.is_displayed()
                            enabled = element.is_enabled()
                            name = element.get_attribute('name') or 'sem nome'
                            id_attr = element.get_attribute('id') or 'sem id'
                            print(f"    Elemento {i+1}: name='{name}' id='{id_attr}' displayed={displayed} enabled={enabled}")
                            
                            if displayed and enabled:
                                cpf_field = element
                                logger.info(f"Campo CPF encontrado com seletor: {selector}")
                                break
                        except Exception as inner_e:
                            print(f"    Erro ao verificar elemento {i+1}: {inner_e}")
                    if cpf_field:
                        break
                except Exception as e:
                    print(f"  Erro com seletor {selector}: {e}")
                    continue
            
            if cpf_field:
                # Limpa e preenche CPF/CNPJ
                print("✅ Campo CPF/CNPJ encontrado! Preenchendo...")
                cpf_field.clear()
                time.sleep(0.5)
                cpf_field.send_keys(cpf_cnpj)
                logger.info(f"CPF/CNPJ preenchido: {cpf_cnpj}")
                
                # Destaca o campo
                self.driver.execute_script(
                    "arguments[0].style.backgroundColor='lightgreen';" +
                    "arguments[0].style.border='2px solid green';",
                    cpf_field
                )
            else:
                print("❌ Campo CPF/CNPJ não encontrado com nenhum seletor")
                print("\n💡 SOLUÇÃO MANUAL:")
                print("1. Veja o navegador aberto")
                print("2. Preencha manualmente o campo CPF/CNPJ")
                print("3. Pressione Enter para continuar")
                input("Pressione Enter após preencher manualmente...")
                return True  # Continua o processo
            
            print("✅ UC e CPF/CNPJ preenchidos com sucesso!")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao preencher UC e CPF: {e}")
            return False
        
    def step1_submit(self):
        """Etapa 1: Clica no botão Entrar - VERSÃO CORRIGIDA"""
        try:
            print("\n🚀 ETAPA 1: Clicando no botão 'Entrar'...")
            
            # Aguarda um pouco antes de procurar o botão
            time.sleep(2)
            
            # SELETORES CORRIGIDOS baseados no HTML fornecido
            submit_selectors = [
                # Seletor específico para o botão do HTML fornecido
                "button.button[onclick*='ValidarCamposAreaLogada']",
                "button.button",
                # Seletores mais genéricos
                "button:contains('Entrar')",
                "button:contains('ENTRAR')",
                "button[type='button']:contains('Entrar')",
                # Backup para inputs (caso existam)
                "input[value*='Entrar' i]",
                "input[type='submit'][value*='Entrar' i]",
                # Por texto usando XPath como fallback
            ]
            
            submit_button = None
            
            # Primeiro tenta com CSS selectors
            for selector in submit_selectors:
                try:
                    if ":contains(" in selector:
                        # Para seletores :contains, usar XPath
                        xpath_selector = f"//button[contains(text(), 'Entrar') or contains(text(), 'ENTRAR')]"
                        elements = self.driver.find_elements(By.XPATH, xpath_selector)
                    else:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    
                    print(f"  Testando seletor: {selector} - Encontrados: {len(elements)}")
                    
                    for i, element in enumerate(elements):
                        try:
                            displayed = element.is_displayed()
                            enabled = element.is_enabled()
                            text = element.text.strip() if hasattr(element, 'text') else ''
                            onclick = element.get_attribute('onclick') or ''
                            class_attr = element.get_attribute('class') or ''
                            
                            print(f"    Elemento {i+1}: text='{text}' class='{class_attr}' onclick='{onclick[:50]}...' displayed={displayed} enabled={enabled}")
                            
                            if displayed and enabled:
                                submit_button = element
                                logger.info(f"Botão Entrar encontrado com seletor: {selector}")
                                break
                        except Exception as inner_e:
                            print(f"    Erro ao verificar elemento {i+1}: {inner_e}")
                    
                    if submit_button:
                        break
                        
                except Exception as e:
                    print(f"  Erro com seletor {selector}: {e}")
                    continue
            
            # Se não encontrou com CSS, tenta XPath direto
            if not submit_button:
                print("\n🔍 Tentativa com XPath direto...")
                xpath_selectors = [
                    "//button[contains(@onclick, 'ValidarCamposAreaLogada')]",
                    "//button[@class='button' and contains(text(), 'Entrar')]",
                    "//button[@class='button']",
                    "//button[text()='Entrar']",
                    "//button[contains(text(), 'Entrar')]",
                    "//input[@value='Entrar']"
                ]
                
                for xpath in xpath_selectors:
                    try:
                        elements = self.driver.find_elements(By.XPATH, xpath)
                        print(f"  Testando XPath: {xpath} - Encontrados: {len(elements)}")
                        
                        for i, element in enumerate(elements):
                            try:
                                displayed = element.is_displayed()
                                enabled = element.is_enabled()
                                text = element.text.strip() if hasattr(element, 'text') else ''
                                print(f"    Elemento {i+1}: text='{text}' displayed={displayed} enabled={enabled}")
                                
                                if displayed and enabled:
                                    submit_button = element
                                    logger.info(f"Botão Entrar encontrado com XPath: {xpath}")
                                    break
                            except Exception as inner_e:
                                print(f"    Erro ao verificar elemento {i+1}: {inner_e}")
                        
                        if submit_button:
                            break
                    except Exception as e:
                        print(f"  Erro com XPath {xpath}: {e}")
                        continue
            
            if submit_button:
                # Destaca o botão
                try:
                    self.driver.execute_script(
                        "arguments[0].style.border='3px solid blue';" +
                        "arguments[0].style.backgroundColor='lightblue';",
                        submit_button
                    )
                except:
                    pass  # Ignora erro de styling
                
                print("🎯 Botão 'Entrar' encontrado - clicando...")
                time.sleep(1)
                
                # Tenta diferentes métodos de clique
                click_success = False
                
                # Método 1: Clique normal
                try:
                    submit_button.click()
                    click_success = True
                    logger.info("Botão 'Entrar' clicado com método normal")
                except Exception as e1:
                    print(f"  Método 1 (click normal) falhou: {e1}")
                    
                    # Método 2: JavaScript click
                    try:
                        self.driver.execute_script("arguments[0].click();", submit_button)
                        click_success = True
                        logger.info("Botão 'Entrar' clicado com JavaScript")
                    except Exception as e2:
                        print(f"  Método 2 (JS click) falhou: {e2}")
                        
                        # Método 3: Executar a função onclick diretamente
                        try:
                            onclick = submit_button.get_attribute('onclick')
                            if onclick and 'ValidarCamposAreaLogada' in onclick:
                                self.driver.execute_script("ValidarCamposAreaLogada();")
                                click_success = True
                                logger.info("Botão 'Entrar' acionado via função JavaScript")
                            else:
                                print(f"  Método 3: onclick não encontrado ou inválido: {onclick}")
                        except Exception as e3:
                            print(f"  Método 3 (JS function) falhou: {e3}")
                
                if click_success:
                    print("✅ Clique no botão 'Entrar' realizado com sucesso!")
                    # Aguarda navegação para próxima página
                    time.sleep(5)  # Aumentei o tempo de espera
                    return True
                else:
                    print("❌ Todos os métodos de clique falharam")
                    return False
                
            else:
                print("❌ Botão 'Entrar' não encontrado com nenhum método")
                print("\n🔧 Executando debug completo...")
                self.debug_page_elements()
                
                print("\n💡 SOLUÇÃO MANUAL:")
                print("1. Veja o navegador aberto")
                print("2. Clique manualmente no botão 'Entrar'")
                print("3. Pressione Enter aqui para continuar")
                input("Pressione Enter após clicar manualmente...")
                return True
                
        except Exception as e:
            logger.error(f"Erro ao clicar em 'Entrar': {e}")
            return False


#-------------- Passo 2 ----------#
    def step2_fill_birth_date(self, data_nascimento):
        """Etapa 2: Preenche data de nascimento - VERSÃO CORRIGIDA"""
        try:
            print(f"\n📝 ETAPA 2: Preenchendo data de nascimento ({data_nascimento})...")
            
            # Aguarda a nova página carregar
            time.sleep(3)
            
            print(f"🔍 URL atual: {self.driver.current_url}")
            
            # SELETORES CORRIGIDOS baseados no HTML fornecido
            data_selectors = [
                # Seletor específico do HTML fornecido
                "input[name='ctl00$WEBDOOR$headercorporativogo$txtData']",
                "input[id='WEBDOOR_headercorporativogo_txtData']",
                # Seletores de backup
                "input[name*='txtData']",
                "input[id*='txtData']",
                "input[placeholder*='DD/MM/YYYY']",
                "input[placeholder*='DD/MM/YY']",
                "input[name*='DataNascimento']",
                "input[id*='DataNascimento']",
                "input[name*='data'][class*='numero-cliente']",
                "input[placeholder*='nascimento' i]",
                "input[placeholder*='data' i]",
                "input[type='text'][maxlength='10']"
            ]
            
            data_field = None
            for selector in data_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    print(f"  Testando seletor: {selector} - Encontrados: {len(elements)}")
                    
                    for i, element in enumerate(elements):
                        try:
                            displayed = element.is_displayed()
                            enabled = element.is_enabled()
                            name = element.get_attribute('name') or 'sem nome'
                            id_attr = element.get_attribute('id') or 'sem id'
                            placeholder = element.get_attribute('placeholder') or 'sem placeholder'
                            print(f"    Elemento {i+1}: name='{name}' id='{id_attr}' placeholder='{placeholder}' displayed={displayed} enabled={enabled}")
                            
                            if displayed and enabled:
                                data_field = element
                                logger.info(f"Campo data encontrado com seletor: {selector}")
                                break
                        except Exception as inner_e:
                            print(f"    Erro ao verificar elemento {i+1}: {inner_e}")
                    
                    if data_field:
                        break
                except Exception as e:
                    print(f"  Erro com seletor {selector}: {e}")
                    continue
            
            if data_field:
                # Limpa o campo primeiro
                print("✅ Campo de data encontrado! Preenchendo...")
                try:
                    data_field.clear()
                except:
                    # Se clear() falhar, tenta com JavaScript
                    self.driver.execute_script("arguments[0].value = '';", data_field)
                
                time.sleep(0.5)
                
                # Preenche a data
                data_field.send_keys(data_nascimento)
                logger.info(f"Data de nascimento preenchida: {data_nascimento}")
                
                # Destaca o campo
                self.driver.execute_script(
                    "arguments[0].style.backgroundColor='lightgreen';" +
                    "arguments[0].style.border='2px solid green';",
                    data_field
                )
                
                # Verifica se a data foi preenchida corretamente
                valor_atual = data_field.get_attribute('value')
                print(f"✅ Data preenchida com sucesso! Valor atual: '{valor_atual}'")
                return True
            else:
                print("❌ Campo de data de nascimento não encontrado com nenhum seletor")
                print("\n🔧 Executando debug para encontrar o campo...")
                self.debug_page_elements()
                
                print("\n💡 SOLUÇÃO MANUAL:")
                print("1. Veja o navegador aberto")
                print("2. Preencha manualmente o campo de data de nascimento")
                print("3. Pressione Enter aqui para continuar")
                input("Pressione Enter após preencher manualmente...")
                return True  # Continua o processo
                
        except Exception as e:
            logger.error(f"Erro ao preencher data de nascimento: {e}")
            return False

    def step2_submit(self):
        """Etapa 2: Clica no botão Validar - VERSÃO CORRIGIDA"""
        try:
            print("\n🚀 ETAPA 2: Clicando no botão 'Validar'...")
            
            time.sleep(2)  # Aguarda um pouco antes de procurar o botão
            
            # SELETORES CORRIGIDOS baseados no HTML fornecido
            validate_selectors = [
                # Seletor específico do HTML fornecido
                "input[name='ctl00$WEBDOOR$headercorporativogo$btnValidar']",
                "input[id='WEBDOOR_headercorporativogo_btnValidar']",
                # Seletores de backup
                "input[value='Validar']",
                "input[name*='btnValidar']",
                "input[id*='btnValidar']",
                "input[type='submit'][value*='Validar' i]",
                "input[class='button'][value*='Validar' i]",
                "button:contains('Validar')",
                "input[value*='Confirmar' i]",
                "input[value*='OK' i]"
            ]
            
            validate_button = None
            for selector in validate_selectors:
                try:
                    if ":contains(" in selector:
                        # Para seletores :contains, usar XPath
                        xpath_selector = "//button[contains(text(), 'Validar') or contains(text(), 'VALIDAR')]"
                        elements = self.driver.find_elements(By.XPATH, xpath_selector)
                    else:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    
                    print(f"  Testando seletor: {selector} - Encontrados: {len(elements)}")
                    
                    for i, element in enumerate(elements):
                        try:
                            displayed = element.is_displayed()
                            enabled = element.is_enabled()
                            value = element.get_attribute('value') or ''
                            name = element.get_attribute('name') or 'sem nome'
                            id_attr = element.get_attribute('id') or 'sem id'
                            print(f"    Elemento {i+1}: name='{name}' id='{id_attr}' value='{value}' displayed={displayed} enabled={enabled}")
                            
                            if displayed and enabled:
                                validate_button = element
                                logger.info(f"Botão Validar encontrado com seletor: {selector}")
                                break
                        except Exception as inner_e:
                            print(f"    Erro ao verificar elemento {i+1}: {inner_e}")
                    
                    if validate_button:
                        break
                except Exception as e:
                    print(f"  Erro com seletor {selector}: {e}")
                    continue
            
            if validate_button:
                # Destaca o botão
                try:
                    self.driver.execute_script(
                        "arguments[0].style.border='3px solid blue';" +
                        "arguments[0].style.backgroundColor='lightblue';",
                        validate_button
                    )
                except:
                    pass  # Ignora erro de styling
                
                print("🎯 Botão 'Validar' encontrado - clicando...")
                time.sleep(1)
                
                # Tenta diferentes métodos de clique
                click_success = False
                
                # Método 1: Clique normal
                try:
                    validate_button.click()
                    click_success = True
                    logger.info("Botão 'Validar' clicado com método normal")
                except Exception as e1:
                    print(f"  Método 1 (click normal) falhou: {e1}")
                    
                    # Método 2: JavaScript click
                    try:
                        self.driver.execute_script("arguments[0].click();", validate_button)
                        click_success = True
                        logger.info("Botão 'Validar' clicado com JavaScript")
                    except Exception as e2:
                        print(f"  Método 2 (JS click) falhou: {e2}")
                        
                        # Método 3: Submit do formulário (para inputs type=submit)
                        try:
                            # Tenta encontrar o formulário pai e fazer submit
                            form = validate_button.find_element(By.XPATH, "./ancestor::form[1]")
                            form.submit()
                            click_success = True
                            logger.info("Formulário submetido via form.submit()")
                        except Exception as e3:
                            print(f"  Método 3 (form submit) falhou: {e3}")
                            
                            # Método 4: Executar a função onclick do HTML
                            try:
                                onclick = validate_button.get_attribute('onclick')
                                if onclick and 'WebForm_DoPostBackWithOptions' in onclick:
                                    self.driver.execute_script(onclick)
                                    click_success = True
                                    logger.info("Botão 'Validar' acionado via função onclick")
                                else:
                                    print(f"  Método 4: onclick não encontrado ou inválido")
                            except Exception as e4:
                                print(f"  Método 4 (onclick) falhou: {e4}")
                
                if click_success:
                    print("✅ Clique no botão 'Validar' realizado com sucesso!")
                    # Aguarda processamento/navegação
                    time.sleep(5)  # Aumentei o tempo de espera
                    return True
                else:
                    print("❌ Todos os métodos de clique falharam")
                    print("\n💡 SOLUÇÃO MANUAL:")
                    print("1. Veja o navegador aberto")
                    print("2. Clique manualmente no botão 'Validar'")
                    print("3. Pressione Enter aqui para continuar")
                    input("Pressione Enter após clicar manualmente...")
                    return True
                    
            else:
                print("❌ Botão 'Validar' não encontrado com nenhum seletor")
                print("\n🔧 Executando debug completo...")
                self.debug_page_elements()
                
                print("\n💡 SOLUÇÃO MANUAL:")
                print("1. Veja o navegador aberto")
                print("2. Clique manualmente no botão 'Validar'")
                print("3. Pressione Enter aqui para continuar")
                input("Pressione Enter após clicar manualmente...")
                return True
                
        except Exception as e:
            logger.error(f"Erro ao clicar em 'Validar': {e}")
            return False

#-------------- Passo 3 ----------#

#-------------- ELIMINIADO -------#

#-------------- Passo 4 ----------#
    def step4_navigate_to_invoices(self):
        """Etapa 4: Navega diretamente para Segunda Via após login"""
        try:
            print("\n🧭 ETAPA 4: Navegando diretamente para Segunda Via...")
            
            # Aguarda um pouco para garantir que o login foi processado
            time.sleep(3)
            
            # URL direta da Segunda Via
            segunda_via_url = "https://goias.equatorialenergia.com.br/AgenciaGO/Servi%C3%A7os/aberto/SegundaVia.aspx"
            
            # Navega diretamente para a URL
            print(f"🌐 Acessando diretamente: {segunda_via_url}")
            self.driver.get(segunda_via_url)
            
            # Aguarda a página carregar
            time.sleep(3)
            
            # Verifica se chegou na página correta
            current_url = self.driver.current_url
            page_title = self.driver.title
            
            print(f"📍 URL atual: {current_url}")
            print(f"📄 Título da página: {page_title}")
            
            # Verifica se a navegação foi bem-sucedida
            if "SegundaVia.aspx" in current_url:
                print("✅ Navegação direta para Segunda Via realizada com sucesso!")
                
                # Verifica se tem elementos esperados da página
                try:
                    # Procura pelo dropdown de UCs que deve estar presente
                    uc_dropdown = self.driver.find_elements(By.CSS_SELECTOR, "#CONTENT_comboBoxUC")
                    if uc_dropdown and uc_dropdown[0].is_displayed():
                        print("✅ Página de Segunda Via carregada corretamente - dropdown de UCs encontrado")
                        self.logged_in = True
                        return True
                    else:
                        print("⚠️ Página carregada mas dropdown de UCs não encontrado")
                        # Ainda assim retorna True pois a navegação funcionou
                        self.logged_in = True
                        return True
                        
                except Exception as e:
                    print(f"⚠️ Erro ao verificar elementos da página: {e}")
                    # Mesmo com erro, se a URL está correta, considera sucesso
                    self.logged_in = True
                    return True
                    
            else:
                print("❌ Não foi possível navegar para Segunda Via")
                print("🔧 Tentando análise da página atual...")
                self.debug_page_elements()
                
                # Permite intervenção manual
                print("\n💡 SOLUÇÃO MANUAL:")
                print("1. Verifique se você está logado")
                print("2. Navegue manualmente para Segunda Via se necessário")
                print("3. Pressione Enter para continuar")
                input("Pressione Enter após chegar na página de Segunda Via...")
                return True
                
        except Exception as e:
            logger.error(f"Erro ao navegar para Segunda Via: {e}")
            print(f"❌ Erro ao acessar Segunda Via: {e}")
            return False
        

#-------------- Passo 5 ----------#
    def step5_extract_ucs_and_create_structure(self):
        """Etapa 5: Extrai UCs, cria pasta do cliente e arquivo relatorio.json"""
        try:
            print("\n📁 ETAPA 5: Extraindo UCs e criando estrutura de relatório...")
            
            # Aguarda carregamento da página
            time.sleep(3)
            
            current_url = self.driver.current_url
            print(f"🔍 URL atual: {current_url}")
            print(f"📄 Título da página: {self.driver.title}")
            
            # 1. EXTRAIR NOME DO CLIENTE
            print("\n👤 Extraindo nome do cliente...")
            
            client_name = None
            full_client_name = None
            
            # Estratégia 1: Procurar especificamente no padrão da Enel
            print("🔍 Procurando no padrão da Enel (Olá <strong>NOME</strong>)...")
            
            try:
                # Procura pelo elemento específico da mensagem de boas-vindas
                welcome_selectors = [
                    "#CONTENT_lblMensagemUsuarioGrupoB",
                    "span.mensagem-usuario",
                    "span[id*='lblMensagem']",
                    "span[id*='MensagemUsuario']"
                ]
                
                for selector in welcome_selectors:
                    try:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        for element in elements:
                            # Procura por elemento <strong> dentro do span
                            strong_elements = element.find_elements(By.TAG_NAME, "strong")
                            if strong_elements:
                                full_name = strong_elements[0].text.strip()
                                if full_name and len(full_name) > 3:
                                    full_client_name = full_name
                                    # Cria nome simplificado (apenas primeiro e último nome)
                                    name_parts = full_name.split()
                                    if len(name_parts) >= 2:
                                        client_name = f"{name_parts[0]} {name_parts[-1]}"
                                    else:
                                        client_name = full_name
                                    print(f"✅ Nome completo encontrado: '{full_client_name}'")
                                    print(f"✅ Nome simplificado para pasta: '{client_name}'")
                                    break
                        if client_name:
                            break
                    except Exception as e:
                        print(f"Erro ao buscar com seletor {selector}: {e}")
                        continue
                        
            except Exception as e:
                print(f"Erro na estratégia 1: {e}")
            
            # Estratégia 2: Procurar por XPath mais específico
            if not client_name:
                print("🔍 Procurando por XPath específico...")
                
                xpath_patterns = [
                    # Procura especificamente por "Olá" seguido de <strong>
                    "//span[contains(text(), 'Olá')]/strong",
                    "//span[contains(text(), 'bem vindo') or contains(text(), 'bem-vindo')]/strong",
                    "//p[contains(text(), 'Olá')]//strong",
                    # Procura por qualquer strong que tenha um nome completo
                    "//strong[string-length(normalize-space(text())) > 10 and contains(normalize-space(text()), ' ')]"
                ]
                
                for xpath in xpath_patterns:
                    try:
                        elements = self.driver.find_elements(By.XPATH, xpath)
                        for element in elements:
                            text = element.text.strip()
                            if text and len(text) > 5 and ' ' in text:
                                # Verifica se parece com um nome (não contém números ou símbolos estranhos)
                                if not any(char.isdigit() for char in text) and text.replace(' ', '').isalpha():
                                    full_client_name = text
                                    # Cria nome simplificado
                                    name_parts = text.split()
                                    if len(name_parts) >= 2:
                                        client_name = f"{name_parts[0]} {name_parts[-1]}"
                                    else:
                                        client_name = text
                                    print(f"✅ Nome encontrado via XPath: '{full_client_name}'")
                                    print(f"✅ Nome simplificado: '{client_name}'")
                                    break
                        if client_name:
                            break
                    except Exception as e:
                        print(f"Erro com XPath {xpath}: {e}")
                        continue
            
            # Estratégia 3: Procurar por padrão de mensagem de boas-vindas
            if not client_name:
                print("🔍 Procurando por padrão de mensagem de boas-vindas...")
                
                try:
                    # Procura por elementos que contenham "Olá" ou "bem-vindo"
                    welcome_elements = self.driver.find_elements(By.XPATH, 
                        "//*[contains(text(), 'Olá') or contains(text(), 'bem vindo') or contains(text(), 'bem-vindo')]")
                    
                    for element in welcome_elements:
                        try:
                            # Pega o texto completo do elemento
                            full_text = element.text.strip()
                            print(f"🔍 Analisando texto: '{full_text[:100]}...'")
                            
                            # Procura por padrão "Olá NOME"
                            import re
                            pattern = r'Olá\s+([A-ZÁÊÇÕ\s]+?)(?:,|\s+seja|\s+bem)'
                            match = re.search(pattern, full_text, re.IGNORECASE)
                            
                            if match:
                                full_client_name = match.group(1).strip()
                                # Cria nome simplificado
                                name_parts = full_client_name.split()
                                if len(name_parts) >= 2:
                                    client_name = f"{name_parts[0]} {name_parts[-1]}"
                                else:
                                    client_name = full_client_name
                                print(f"✅ Nome extraído via regex: '{full_client_name}'")
                                print(f"✅ Nome simplificado: '{client_name}'")
                                break
                                
                        except Exception as e:
                            print(f"Erro ao processar elemento: {e}")
                            continue
                            
                except Exception as e:
                    print(f"Erro na estratégia 3: {e}")
            
            # Estratégia 4: Debug - mostra todos os elementos strong da página
            if not client_name:
                print("🔍 Debug: Analisando todos os elementos <strong> da página...")
                try:
                    all_strong = self.driver.find_elements(By.TAG_NAME, "strong")
                    print(f"Encontrados {len(all_strong)} elementos <strong>:")
                    
                    for i, strong in enumerate(all_strong):
                        try:
                            text = strong.text.strip()
                            if text:
                                print(f"   Strong {i+1}: '{text}'")
                                # Se parece com um nome (tem espaços, não tem números, é alfabético)
                                if (len(text) > 5 and ' ' in text and 
                                    not any(char.isdigit() for char in text) and 
                                    text.replace(' ', '').replace('Ç', 'C').replace('Ã', 'A').isalpha()):
                                    full_client_name = text
                                    name_parts = text.split()
                                    if len(name_parts) >= 2:
                                        client_name = f"{name_parts[0]} {name_parts[-1]}"
                                    else:
                                        client_name = text
                                    print(f"✅ Nome identificado automaticamente: '{client_name}'")
                                    break
                        except:
                            continue
                            
                except Exception as e:
                    print(f"Erro no debug: {e}")
            
            # Nome padrão se não encontrar
            if not client_name:
                from datetime import datetime
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                
                # Tenta pelo menos pegar o CPF para identificar
                try:
                    cpf_elements = self.driver.find_elements(By.XPATH, "//*[contains(text(), '***') and contains(text(), '**')]")
                    if cpf_elements:
                        cpf_masked = cpf_elements[0].text.strip()
                        client_name = f"Cliente_CPF_{cpf_masked.replace('*', 'X').replace('.', '').replace('-', '')}_{timestamp}"
                        full_client_name = client_name
                    else:
                        client_name = f"Cliente_{timestamp}"
                        full_client_name = client_name
                except:
                    client_name = f"Cliente_{timestamp}"
                    full_client_name = client_name
                    
                print(f"⚠️ Nome do cliente não encontrado, usando identificador: '{client_name}'")
            
            # Sanitiza o nome para usar como nome de pasta
            import re
            safe_client_name = re.sub(r'[<>:"/\\|?*]', '_', client_name)
            safe_client_name = safe_client_name.strip()
            
            # Converte para Title Case (primeira letra de cada palavra maiúscula)
            safe_client_name = safe_client_name.title()
            
            print(f"📁 Nome da pasta: '{safe_client_name}'")
            print(f"👤 Nome completo: '{full_client_name or client_name}'")
            
            # 2. EXTRAIR UCS DO DROPDOWN
            print("\n🔍 Extraindo UCs do dropdown...")
            
            uc_dropdown = None
            dropdown_selectors = [
                "select[name*='comboBoxUC']",
                "select[id*='comboBoxUC']",
                "#CONTENT_comboBoxUC",
                "select.DropDown",
                "select[name*='UC']"
            ]
            
            for selector in dropdown_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        if element.is_displayed():
                            uc_dropdown = element
                            print(f"✅ Dropdown de UCs encontrado: {selector}")
                            break
                    if uc_dropdown:
                        break
                except:
                    continue
            
            if not uc_dropdown:
                print("❌ Dropdown de UCs não encontrado!")
                self.debug_page_elements()
                return False
            
            # Extrai todas as opções do dropdown
            try:
                from selenium.webdriver.support.ui import Select
                select = Select(uc_dropdown)
                options = select.options
                
                ucs_list = []
                for option in options:
                    uc_number = option.get_attribute('value').strip()
                    if uc_number:  # Ignora opções vazias
                        ucs_list.append(uc_number)
                
                print(f"✅ {len(ucs_list)} UCs encontradas:")
                for i, uc in enumerate(ucs_list, 1):
                    print(f"   UC {i}: {uc}")
                    
            except Exception as e:
                print(f"❌ Erro ao extrair UCs do dropdown: {e}")
                return False
            
            if not ucs_list:
                print("❌ Nenhuma UC encontrada no dropdown!")
                return False
            
            # 3. CRIAR ESTRUTURA DE PASTAS E ARQUIVO JSON
            print(f"\n📁 Criando estrutura de pastas para '{safe_client_name}'...")
            
            import os
            import json
            from datetime import datetime
            
            # Cria pasta principal do cliente
            base_folder = "clientes_faturas"
            client_folder = os.path.join(base_folder, safe_client_name)
            
            try:
                os.makedirs(client_folder, exist_ok=True)
                print(f"✅ Pasta criada: {client_folder}")
            except Exception as e:
                print(f"❌ Erro ao criar pasta: {e}")
                return False
            
            # 4. CRIAR ARQUIVO RELATORIO.JSON
            print("\n📄 Criando arquivo relatorio.json...")
            
            current_datetime = datetime.now()
            report_data = {
                "cliente": full_client_name or client_name,  # Usa o nome completo no JSON
                "data_busca": current_datetime.strftime("%d/%m/%Y %H:%M:%S"),
                "total_ucs": len(ucs_list),
                "ucs": []
            }
            
            # Adiciona cada UC com estrutura inicial (simplificada)
            for i, uc in enumerate(ucs_list, 1):
                uc_data = {
                    "uc": uc,                   # Apenas o número da UC
                    "faturas_em_aberto": None,  # Será preenchido posteriormente
                    "meses_referencia": [],     # Será preenchido posteriormente
                    "valor_total_devido": None, # Será preenchido posteriormente
                    "status_processamento": "pendente"
                }
                report_data["ucs"].append(uc_data)
            
            # Salva o arquivo JSON
            json_file_path = os.path.join(client_folder, "relatorio.json")
            try:
                with open(json_file_path, 'w', encoding='utf-8') as f:
                    json.dump(report_data, f, indent=4, ensure_ascii=False)
                print(f"✅ Arquivo relatorio.json criado: {json_file_path}")
            except Exception as e:
                print(f"❌ Erro ao criar arquivo JSON: {e}")
                return False
            
            # 5. SALVAR INFORMAÇÕES NA CLASSE PARA USAR DEPOIS
            self.client_name = full_client_name or client_name
            self.safe_client_name = safe_client_name
            self.client_folder = client_folder
            self.json_file_path = json_file_path
            self.ucs_list = ucs_list
            self.current_report_data = report_data
            
            print(f"\n✅ ETAPA 5 CONCLUÍDA COM SUCESSO!")
            print(f"📊 Resumo:")
            print(f"   👤 Cliente: {full_client_name or client_name}")
            print(f"   📁 Pasta: {client_folder}")
            print(f"   🔢 Total de UCs: {len(ucs_list)}")
            print(f"   📄 Arquivo JSON: relatorio.json")
            print(f"   📅 Data/Hora: {current_datetime.strftime('%d/%m/%Y %H:%M:%S')}")
            
            # Mostra preview do JSON criado
            print(f"\n📋 Preview do relatório JSON:")
            print(json.dumps(report_data, indent=2, ensure_ascii=False)[:500] + "...")
            
            return True
            
        except Exception as e:
            logger.error(f"Erro na etapa 5: {e}")
            print(f"❌ Erro inesperado na etapa 5: {e}")
            return False

    def update_report_json(self, uc_number, updates):
        """Função auxiliar para atualizar dados de uma UC específica no JSON"""
        try:
            # Carrega o JSON atual
            with open(self.json_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Encontra a UC e atualiza
            for uc_data in data["ucs"]:
                if uc_data["uc"] == uc_number:  # Mudança aqui: agora usa "uc" em vez de "numero_uc"
                    uc_data.update(updates)
                    break
            
            # Salva o arquivo atualizado
            with open(self.json_file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            
            print(f"✅ JSON atualizado para UC {uc_number}")
            return True
            
        except Exception as e:
            print(f"❌ Erro ao atualizar JSON: {e}")
            return False


#-------------- Passo 6 Corrigido ----------#
    def step6_process_each_uc(self):
            """Etapa 6: Processa cada UC individualmente, configurando formulário e navegando para faturas"""
            try:
                print("\n📋 ETAPA 6: Processando cada UC individualmente...")
                
                if not hasattr(self, 'ucs_list') or not self.ucs_list:
                    print("❌ Lista de UCs não encontrada! Execute o Step 5 primeiro.")
                    return False
                
                print(f"🔢 Total de UCs para processar: {len(self.ucs_list)}")
                
                # Para cada UC, executa o processo
                for i, uc_number in enumerate(self.ucs_list, 1):
                    print(f"\n{'='*60}")
                    print(f"🔄 PROCESSANDO UC {i}/{len(self.ucs_list)}: {uc_number}")
                    print(f"{'='*60}")
                    
                    # Processa a UC atual
                    if self.process_single_uc(uc_number, i):
                        print(f"✅ UC {uc_number} processada com sucesso!")
                        
                        # Atualiza o JSON com status de sucesso
                        self.update_report_json(uc_number, {
                            "status_processamento": "processada_com_sucesso",
                            "data_processamento": datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                        })
                    else:
                        print(f"❌ Erro ao processar UC {uc_number}")
                        
                        # Atualiza o JSON com status de erro
                        self.update_report_json(uc_number, {
                            "status_processamento": "erro_no_processamento",
                            "data_processamento": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                            "erro": "Falha no processamento individual da UC"
                        })
                    
                    # NOVO: Volta para página de Segunda Via antes da próxima UC (exceto no último)
                    if i < len(self.ucs_list):
                        if self.navigate_back_to_second_copy():
                            time.sleep(2)
                        else:
                            print("⚠️ Aviso: Navegação de volta pode ter falhado, tentando continuar...")
                            time.sleep(2)
                
                print(f"\n✅ ETAPA 6 CONCLUÍDA! Todas as {len(self.ucs_list)} UCs foram processadas.")
                return True
                
            except Exception as e:
                logger.error(f"Erro na etapa 6: {e}")
                print(f"❌ Erro inesperado na etapa 6: {e}")
                return False  

    def process_single_uc(self, uc_number, uc_index):
        """Processa uma UC individual - VERSÃO ATUALIZADA COM STEP 7"""
        try:
            print(f"\n🎯 Processando UC: {uc_number}")
            
            # PASSO 1: Selecionar a UC no dropdown
            if not self.select_uc_in_dropdown(uc_number):
                return False
            
            # PASSO 2: Aguardar página recarregar
            print("⏳ Aguardando página recarregar após seleção da UC...")
            time.sleep(3)
            
            # PASSO 3: Configurar tipo de emissão para "Emitir Fatura Completa"
            if not self.set_emission_type("completa"):
                return False
            
            # PASSO 4: Configurar motivo da emissão para "Outros"
            if not self.set_emission_reason("ESV05"):  # ESV05 = Outros
                return False
            
            # PASSO 5: Clicar no botão "Emitir"
            if not self.click_emit_button():
                return False
            
            # PASSO 6: Aguardar navegação para página de faturas
            print("⏳ Aguardando navegação para página de faturas...")
            time.sleep(4)
            
            # PASSO 7: Verificar se chegou na página de faturas
            if self.verify_invoices_page():
                print(f"✅ Navegação bem-sucedida para faturas da UC {uc_number}")
                
                if self.step7_extract_and_download_invoices(uc_number):
                    print(f"✅ Download de faturas concluído para UC {uc_number}")
                    return True
                else:
                    print(f"⚠️ Problemas no download de faturas da UC {uc_number}")
                    return True  # Retorna True mesmo com problemas para continuar com outras UCs
                                    
            else:
                print(f"❌ Não foi possível acessar faturas da UC {uc_number}")
                return False
            
        except Exception as e:
            print(f"❌ Erro ao processar UC {uc_number}: {e}")
            logger.error(f"Erro ao processar UC {uc_number}: {e}")
            return False

    def navigate_back_to_second_copy(self):
        """Navega de volta para a página de Segunda Via para processar próxima UC"""
        try:
            print("🔄 Navegando de volta para página de Segunda Via...")
            
            # URL da página de Segunda Via
            segunda_via_url = "https://goias.equatorialenergia.com.br/AgenciaGO/Servi%C3%A7os/aberto/SegundaVia.aspx"
            
            # Navega diretamente para a URL
            print(f"🌐 Acessando: {segunda_via_url}")
            self.driver.get(segunda_via_url)
            
            # Aguarda a página carregar
            time.sleep(3)
            
            # Verifica se chegou na página correta
            current_url = self.driver.current_url
            print(f"✅ URL atual após navegação: {current_url}")
            
            # Verifica se contém os indicadores da página de Segunda Via
            if ("SegundaVia.aspx" in current_url or 
                "segunda" in current_url.lower() or 
                "via" in current_url.lower()):
                print("✅ Retornou com sucesso para página de Segunda Via")
                return True
            else:
                print("⚠️ URL pode não ser a esperada, mas continuando...")
                print(f"URL atual: {current_url}")
                
                # Verifica se há elementos típicos da página de Segunda Via
                try:
                    # Procura por elementos característicos da página
                    dropdown_uc = self.driver.find_elements(By.CSS_SELECTOR, "#CONTENT_comboBoxUC")
                    if dropdown_uc and dropdown_uc[0].is_displayed():
                        print("✅ Elementos da página de Segunda Via encontrados")
                        return True
                    else:
                        print("⚠️ Elementos da página não encontrados, mas continuando...")
                        return True
                except:
                    print("⚠️ Erro ao verificar elementos, mas continuando...")
                    return True
            
        except Exception as e:
            print(f"❌ Erro ao navegar de volta: {e}")
            logger.error(f"Erro ao navegar de volta para Segunda Via: {e}")
            
            # Tenta uma abordagem alternativa usando o botão back
            try:
                print("🔄 Tentando voltar usando navegação do browser...")
                self.driver.back()
                time.sleep(2)
                
                current_url = self.driver.current_url
                print(f"🌐 URL após voltar: {current_url}")
                
                if "SegundaVia.aspx" in current_url:
                    print("✅ Voltou com sucesso usando browser back")
                    return True
                else:
                    print("⚠️ Browser back não levou à página correta")
                    return False
                    
            except Exception as e2:
                print(f"❌ Erro também na abordagem alternativa: {e2}")
                return False

    def select_uc_in_dropdown(self, uc_number):
        """Seleciona uma UC específica no dropdown"""
        try:
            print(f"🔍 Selecionando UC {uc_number} no dropdown...")
            
            # Aguarda um pouco para garantir que a página está carregada
            time.sleep(1)
            
            # Encontra o dropdown de UCs
            dropdown_selectors = [
                "#CONTENT_comboBoxUC",
                "select[name*='comboBoxUC']",
                "select[id*='comboBoxUC']",
                "select.DropDown"
            ]
            
            dropdown = None
            for selector in dropdown_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        if element.is_displayed():
                            dropdown = element
                            print(f"✅ Dropdown encontrado: {selector}")
                            break
                    if dropdown:
                        break
                except:
                    continue
            
            if not dropdown:
                print("❌ Dropdown de UCs não encontrado!")
                return False
            
            # Seleciona a UC específica
            from selenium.webdriver.support.ui import Select
            select = Select(dropdown)
            
            # Tenta selecionar por valor
            try:
                select.select_by_value(uc_number)
                print(f"✅ UC {uc_number} selecionada por valor")
                
                # Aguarda um pouco para o JavaScript processar
                time.sleep(1)
                return True
                
            except Exception as e:
                print(f"❌ Erro ao selecionar UC por valor: {e}")
                
                # Tenta selecionar por texto visível
                try:
                    select.select_by_visible_text(uc_number)
                    print(f"✅ UC {uc_number} selecionada por texto")
                    time.sleep(1)
                    return True
                except Exception as e2:
                    print(f"❌ Erro ao selecionar UC por texto: {e2}")
                    return False
            
        except Exception as e:
            print(f"❌ Erro geral ao selecionar UC: {e}")
            return False

    def set_emission_type(self, emission_type="completa"):
        """Configura o tipo de emissão para 'Emitir fatura completa'"""
        try:
            print("⚙️ Configurando tipo de emissão para 'Emitir fatura completa'...")
            
            # Encontra o dropdown de tipo de emissão
            emission_selectors = [
                "#CONTENT_cbTipoEmissao",
                "select[name*='cbTipoEmissao']",
                "select[id*='cbTipoEmissao']"
            ]
            
            dropdown = None
            for selector in emission_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        if element.is_displayed():
                            dropdown = element
                            print(f"✅ Dropdown tipo emissão encontrado: {selector}")
                            break
                    if dropdown:
                        break
                except:
                    continue
            
            if not dropdown:
                print("❌ Dropdown de tipo de emissão não encontrado!")
                return False
            
            # Seleciona "Emitir fatura completa"
            from selenium.webdriver.support.ui import Select
            select = Select(dropdown)
            
            try:
                select.select_by_value(emission_type)
                print(f"✅ Tipo de emissão '{emission_type}' selecionado")
                time.sleep(1)
                return True
            except Exception as e:
                print(f"❌ Erro ao selecionar tipo de emissão: {e}")
                return False
            
        except Exception as e:
            print(f"❌ Erro geral ao configurar tipo de emissão: {e}")
            return False

    def set_emission_reason(self, reason_code="ESV05"):
        """Configura o motivo da emissão para 'Outros' (ESV05)"""
        try:
            print("⚙️ Configurando motivo da emissão para 'Outros'...")
            
            # Encontra o dropdown de motivo
            reason_selectors = [
                "#CONTENT_cbMotivo",
                "select[name*='cbMotivo']",
                "select[id*='cbMotivo']"
            ]
            
            dropdown = None
            for selector in reason_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        if element.is_displayed():
                            dropdown = element
                            print(f"✅ Dropdown motivo encontrado: {selector}")
                            break
                    if dropdown:
                        break
                except:
                    continue
            
            if not dropdown:
                print("❌ Dropdown de motivo não encontrado!")
                return False
            
            # Seleciona "Outros" (ESV05)
            from selenium.webdriver.support.ui import Select
            select = Select(dropdown)
            
            try:
                select.select_by_value(reason_code)
                print(f"✅ Motivo '{reason_code}' (Outros) selecionado")
                time.sleep(1)
                return True
            except Exception as e:
                print(f"❌ Erro ao selecionar motivo: {e}")
                return False
            
        except Exception as e:
            print(f"❌ Erro geral ao configurar motivo: {e}")
            return False

    def click_emit_button(self):
        """Clica no botão 'Emitir' para processar a segunda via"""
        try:
            print("🔘 Clicando no botão 'Emitir'...")
            
            # Encontra o botão Emitir
            button_selectors = [
                "#CONTENT_btEnviar",
                "input[name*='btEnviar']",
                "input[id*='btEnviar']",
                "input[value='Emitir']",
                ".btEmitir"
            ]
            
            button = None
            for selector in button_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        if element.is_displayed() and element.is_enabled():
                            button = element
                            print(f"✅ Botão Emitir encontrado: {selector}")
                            break
                    if button:
                        break
                except:
                    continue
            
            if not button:
                print("❌ Botão 'Emitir' não encontrado!")
                return False
            
            # Clica no botão
            try:
                # Scroll para o botão para garantir que está visível
                self.driver.execute_script("arguments[0].scrollIntoView(true);", button)
                time.sleep(0.5)
                
                # Clica no botão
                button.click()
                print("✅ Botão 'Emitir' clicado com sucesso")
                return True
                
            except Exception as e:
                print(f"❌ Erro ao clicar no botão: {e}")
                
                # Tenta clicar via JavaScript como alternativa
                try:
                    self.driver.execute_script("arguments[0].click();", button)
                    print("✅ Botão 'Emitir' clicado via JavaScript")
                    return True
                except Exception as e2:
                    print(f"❌ Erro ao clicar via JavaScript: {e2}")
                    return False
            
        except Exception as e:
            print(f"❌ Erro geral ao clicar no botão Emitir: {e}")
            return False

    def verify_invoices_page(self):
        """Verifica se chegou na página de faturas em aberto"""
        try:
            print("🔍 Verificando se chegou na página de faturas...")
            
            # Aguarda um pouco para a página carregar
            time.sleep(2)
            
            current_url = self.driver.current_url
            page_title = self.driver.title
            
            print(f"🌐 URL atual: {current_url}")
            print(f"📄 Título da página: {page_title}")
            
            # Verifica indicadores de que está na página de faturas
            success_indicators = [
                # Textos que podem aparecer na página de faturas
                "faturas em aberto",
                "segunda via",
                "débitos pendentes",
                "conta em aberto",
                "valor devido",
                # IDs/classes específicas
                "fatura",
                "debito",
                "pendente"
            ]
            
            page_source = self.driver.page_source.lower()
            
            found_indicators = []
            for indicator in success_indicators:
                if indicator.lower() in page_source:
                    found_indicators.append(indicator)
            
            if found_indicators:
                print(f"✅ Página de faturas identificada! Indicadores encontrados: {found_indicators}")
                return True
            else:
                print("⚠️ Não foi possível confirmar se está na página de faturas")
                print("🔧 Salvando HTML da página para análise...")
                
                # Salva HTML para debug
                try:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    debug_file = f"debug_invoices_page_{timestamp}.html"
                    with open(debug_file, 'w', encoding='utf-8') as f:
                        f.write(self.driver.page_source)
                    print(f"💾 HTML salvo em: {debug_file}")
                except:
                    pass
                
                return False
            
        except Exception as e:
            print(f"❌ Erro ao verificar página de faturas: {e}")
            return False

    def update_final_report_after_step6(self):
        """Atualiza o relatório JSON com informações do Step 6"""
        try:
            print("\n📊 Atualizando relatório final após Step 6...")
            
            # Carrega o JSON atual
            with open(self.json_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Conta estatísticas
            total_processadas = 0
            total_com_erro = 0
            
            for uc_data in data["ucs"]:
                if uc_data.get("status_processamento") == "processada_com_sucesso":
                    total_processadas += 1
                elif uc_data.get("status_processamento") == "erro_no_processamento":
                    total_com_erro += 1
            
            # Atualiza dados gerais
            data["step6_concluido"] = True
            data["data_step6"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            data["estatisticas_step6"] = {
                "total_ucs": len(self.ucs_list),
                "processadas_com_sucesso": total_processadas,
                "com_erro": total_com_erro,
                "pendentes": len(self.ucs_list) - total_processadas - total_com_erro
            }
            
            # Salva o arquivo atualizado
            with open(self.json_file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            
            print(f"✅ Relatório atualizado!")
            print(f"   📊 UCs processadas: {total_processadas}")
            print(f"   ❌ UCs com erro: {total_com_erro}")
            
            return True
            
        except Exception as e:
            print(f"❌ Erro ao atualizar relatório final: {e}")
            return False



#--------- Passo 7 ------#
    def step7_extract_and_download_invoices(self, uc_number):
        """Etapa 7: Extrai informações das faturas e faz download tratando o popup"""
        try:
            print(f"\n📄 ETAPA 7: Processando faturas da UC {uc_number}...")
            
            # Aguarda a página carregar completamente
            time.sleep(3)
            
            # 1. ENCONTRAR TABELA DE FATURAS
            print("🔍 Procurando tabela de faturas...")
            
            invoice_rows = []
            try:
                # Procura por linhas que contêm links de download
                rows = self.driver.find_elements(By.XPATH, "//tr[.//a[contains(text(), 'Download')]]")
                if rows:
                    invoice_rows = rows
                    print(f"✅ Encontradas {len(rows)} faturas disponíveis")
            except Exception as e:
                print(f"❌ Erro ao procurar faturas: {e}")
            
            if not invoice_rows:
                print("⚠️ Nenhuma fatura encontrada para esta UC")
                self.update_report_json(uc_number, {
                    "faturas_em_aberto": 0,
                    "meses_referencia": [],
                    "valor_total_devido": "0,00",
                    "faturas_baixadas": []
                })
                return True
            
            # 2. EXTRAIR INFORMAÇÕES DAS FATURAS
            faturas_info = []
            meses_referencia = []
            
            for i, row in enumerate(invoice_rows):
                try:
                    # Extrai o mês de referência (primeira coluna)
                    month_elements = row.find_elements(By.XPATH, "./td[1]")
                    if month_elements:
                        month_text = month_elements[0].text.strip()
                        print(f"📅 Fatura {i+1}: {month_text}")
                        meses_referencia.append(month_text)
                        
                        # Encontra o link de download nesta linha
                        download_link = row.find_element(By.XPATH, ".//a[contains(text(), 'Download')]")
                        
                        faturas_info.append({
                            'mes': month_text,
                            'link_element': download_link,
                            'row_index': i
                        })
                        
                except Exception as e:
                    print(f"❌ Erro ao processar linha {i+1}: {e}")
                    continue
            
            # 3. ATUALIZAR JSON COM INFORMAÇÕES DAS FATURAS
            print(f"\n📊 Atualizando relatório JSON...")
            self.update_report_json(uc_number, {
                "faturas_em_aberto": len(faturas_info),
                "meses_referencia": meses_referencia
            })
            
            # 4. CONFIGURAR PASTA DE DOWNLOADS
            uc_folder = os.path.join(self.client_folder, f"UC_{uc_number}")
            try:
                os.makedirs(uc_folder, exist_ok=True)
                print(f"📁 Pasta da UC criada: {uc_folder}")
                
                # Atualiza pasta de download do Chrome para esta UC
                self.update_download_folder_for_client(uc_folder)
                
            except Exception as e:
                print(f"❌ Erro ao criar pasta da UC: {e}")
                uc_folder = self.client_folder
            
            # 5. FAZER DOWNLOAD DE CADA FATURA COM TRATAMENTO DE POPUP
            faturas_baixadas = []
            
            for idx, fatura in enumerate(faturas_info):
                try:
                    print(f"\n💾 Baixando fatura {idx+1}/{len(faturas_info)}: {fatura['mes']}")
                    
                    # Formata o nome do arquivo
                    mes_ano = fatura['mes'].replace('/', '_')
                    mes_parts = mes_ano.split('_')
                    if len(mes_parts) == 2:
                        mes_abrev = mes_parts[0][:3].capitalize()
                        ano_abrev = mes_parts[1][-2:]
                        filename = f"{uc_number}_{mes_abrev}_{ano_abrev}.pdf"
                    else:
                        filename = f"{uc_number}_{mes_ano}.pdf"
                    
                    filepath = os.path.join(uc_folder, filename)
                    
                    # Registra o tempo antes do download
                    start_time = time.time()
                    
                    # CLICA NO LINK DE DOWNLOAD
                    try:
                        # Scroll até o elemento
                        self.driver.execute_script("arguments[0].scrollIntoView(true);", fatura['link_element'])
                        time.sleep(0.5)
                        
                        print("🖱️ Clicando no link de download...")
                        fatura['link_element'].click()
                        
                    except Exception as click_error:
                        print(f"⚠️ Erro no clique, tentando JavaScript: {click_error}")
                        self.driver.execute_script("arguments[0].click();", fatura['link_element'])
                    
                    # AGUARDA E TRATA O POPUP
                    print("⏳ Aguardando popup aparecer...")
                    popup_handled = False
                    max_wait = 10  # segundos
                    wait_time = 0
                    
                    while wait_time < max_wait and not popup_handled:
                        try:
                            # Procura pelo botão OK do popup
                            ok_button = self.driver.find_element(By.CSS_SELECTOR, 
                                "input#CONTENT_btnModal.btn.btn-info.btnModal.ModalButton")
                            
                            if ok_button.is_displayed():
                                print("✅ Popup detectado! Clicando em OK...")
                                
                                # Destaca o botão para debug
                                self.driver.execute_script(
                                    "arguments[0].style.border='3px solid red';",
                                    ok_button
                                )
                                
                                time.sleep(0.5)
                                
                                # Clica no botão OK
                                try:
                                    ok_button.click()
                                except:
                                    self.driver.execute_script("arguments[0].click();", ok_button)
                                
                                popup_handled = True
                                print("✅ Popup tratado com sucesso!")
                                
                                # Aguarda o download começar
                                time.sleep(3)
                                
                        except NoSuchElementException:
                            # Popup ainda não apareceu
                            time.sleep(0.5)
                            wait_time += 0.5
                        except Exception as e:
                            print(f"⚠️ Erro ao procurar popup: {e}")
                            time.sleep(0.5)
                            wait_time += 0.5
                    
                    if not popup_handled:
                        print("⚠️ Popup não apareceu no tempo esperado")
                    
                    # VERIFICA SE O DOWNLOAD FOI INICIADO
                    # Aguarda um tempo adicional para o download completar
                    print("⏳ Aguardando conclusão do download...")
                    time.sleep(5)
                    
                    # Verifica se o arquivo foi baixado
                    download_success = False
                    
                    # Lista arquivos na pasta de downloads
                    try:
                        # Procura por arquivos PDF recentes
                        for file in os.listdir(uc_folder):
                            if file.endswith('.pdf'):
                                file_path = os.path.join(uc_folder, file)
                                # Verifica se o arquivo foi criado após iniciar o download
                                if os.path.getctime(file_path) > start_time:
                                    # Renomeia o arquivo se necessário
                                    if file != filename:
                                        new_path = os.path.join(uc_folder, filename)
                                        os.rename(file_path, new_path)
                                        print(f"✅ Arquivo renomeado para: {filename}")
                                    else:
                                        print(f"✅ Download concluído: {filename}")
                                    
                                    download_success = True
                                    faturas_baixadas.append({
                                        'mes': fatura['mes'],
                                        'arquivo': filename,
                                        'caminho': os.path.join(uc_folder, filename)
                                    })
                                    break
                        
                        if not download_success:
                            # Verifica na pasta de downloads padrão também
                            default_download = os.path.join(os.path.expanduser("~"), "Downloads")
                            for file in os.listdir(default_download):
                                if file.endswith('.pdf'):
                                    file_path = os.path.join(default_download, file)
                                    if os.path.getctime(file_path) > start_time:
                                        # Move o arquivo para a pasta correta
                                        new_path = os.path.join(uc_folder, filename)
                                        import shutil
                                        shutil.move(file_path, new_path)
                                        print(f"✅ Arquivo movido e renomeado: {filename}")
                                        
                                        download_success = True
                                        faturas_baixadas.append({
                                            'mes': fatura['mes'],
                                            'arquivo': filename,
                                            'caminho': new_path
                                        })
                                        break
                        
                    except Exception as e:
                        print(f"❌ Erro ao verificar download: {e}")
                    
                    if not download_success:
                        print(f"⚠️ Download da fatura {fatura['mes']} pode não ter sido concluído")
                    
                    # Volta para a página de faturas se necessário
                    # O popup pode ter mudado a página, então verificamos
                    current_url = self.driver.current_url
                    if "mostrarFaturaCompleta" in current_url:
                        print("🔙 Voltando para lista de faturas...")
                        self.driver.back()
                        time.sleep(3)
                        
                        # Se houver mais faturas, precisa re-encontrar os elementos
                        if idx < len(faturas_info) - 1:
                            print("🔄 Re-localizando elementos da página...")
                            rows = self.driver.find_elements(By.XPATH, "//tr[.//a[contains(text(), 'Download')]]")
                            # Atualiza os links para as próximas faturas
                            for j in range(idx + 1, len(faturas_info)):
                                if j - idx - 1 < len(rows):
                                    next_row = rows[faturas_info[j]['row_index']]
                                    next_link = next_row.find_element(By.XPATH, ".//a[contains(text(), 'Download')]")
                                    faturas_info[j]['link_element'] = next_link
                    
                except Exception as e:
                    print(f"❌ Erro ao baixar fatura {fatura['mes']}: {e}")
                    continue
            
            # 6. ATUALIZAR JSON COM FATURAS BAIXADAS
            print(f"\n📊 Atualizando relatório com {len(faturas_baixadas)} faturas baixadas...")
            self.update_report_json(uc_number, {
                "faturas_baixadas": faturas_baixadas,
                "download_concluido": len(faturas_baixadas) > 0,
                "data_download": datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            })
            
            print(f"\n✅ ETAPA 7 CONCLUÍDA para UC {uc_number}!")
            print(f"📊 Resumo:")
            print(f"   🔢 Faturas encontradas: {len(faturas_info)}")
            print(f"   💾 Faturas baixadas: {len(faturas_baixadas)}")
            print(f"   📁 Pasta: {uc_folder}")
            
            return True
            
        except Exception as e:
            logger.error(f"Erro no Step 7 para UC {uc_number}: {e}")
            print(f"❌ Erro no Step 7: {e}")
            
            self.update_report_json(uc_number, {
                "erro_download": str(e),
                "download_concluido": False
            })
            
            return False

    def wait_for_download_complete(self, download_folder, timeout=30):
        """Aguarda o download ser concluído verificando arquivos .crdownload"""
        try:
            print("⏳ Monitorando pasta de downloads...")
            
            end_time = time.time() + timeout
            while time.time() < end_time:
                # Verifica se há arquivos temporários do Chrome
                temp_files = [f for f in os.listdir(download_folder) if f.endswith('.crdownload')]
                
                if not temp_files:
                    # Não há downloads em andamento
                    time.sleep(1)  # Aguarda mais um pouco para garantir
                    
                    # Procura por PDFs recentes
                    pdf_files = [f for f in os.listdir(download_folder) if f.endswith('.pdf')]
                    if pdf_files:
                        # Ordena por data de criação (mais recente primeiro)
                        pdf_files.sort(key=lambda x: os.path.getctime(os.path.join(download_folder, x)), reverse=True)
                        most_recent = pdf_files[0]
                        
                        # Verifica se foi criado nos últimos 30 segundos
                        file_path = os.path.join(download_folder, most_recent)
                        if time.time() - os.path.getctime(file_path) < 30:
                            print(f"✅ Download concluído: {most_recent}")
                            return file_path
                        
                    return None
                else:
                    print(f"⏳ Download em andamento: {temp_files[0]}")
                    time.sleep(1)
            
            print("⚠️ Timeout ao aguardar download")
            return None
            
        except Exception as e:
            print(f"❌ Erro ao monitorar download: {e}")
            return None

    def handle_popup_and_download(self, uc_number, fatura_info, uc_folder):
        """Função específica para lidar com o popup e gerenciar o download"""
        try:
            mes_ano = fatura_info['mes'].replace('/', '_')
            mes_parts = mes_ano.split('_')
            if len(mes_parts) == 2:
                mes_abrev = mes_parts[0][:3].capitalize()
                ano_abrev = mes_parts[1][-2:]
                filename = f"{uc_number}_{mes_abrev}_{ano_abrev}.pdf"
            else:
                filename = f"{uc_number}_{mes_ano}.pdf"
            
            # Lista arquivos antes do download
            files_before = set(os.listdir(uc_folder)) if os.path.exists(uc_folder) else set()
            
            # Clica no link
            print("🖱️ Clicando no link de download...")
            self.driver.execute_script("arguments[0].scrollIntoView(true);", fatura_info['link_element'])
            time.sleep(0.5)
            fatura_info['link_element'].click()
            
            # Aguarda e trata o popup
            popup_found = False
            for i in range(20):  # Tenta por 10 segundos
                try:
                    # Múltiplos seletores para o botão OK
                    ok_selectors = [
                        "input#CONTENT_btnModal",
                        "input.btnModal",
                        "button.ModalButton",
                        "input[value='OK']",
                        "button:contains('OK')"
                    ]
                    
                    for selector in ok_selectors:
                        try:
                            if ":contains(" in selector:
                                ok_buttons = self.driver.find_elements(By.XPATH, "//button[text()='OK']")
                            else:
                                ok_buttons = self.driver.find_elements(By.CSS_SELECTOR, selector)
                            
                            for button in ok_buttons:
                                if button.is_displayed():
                                    print(f"✅ Botão OK encontrado com seletor: {selector}")
                                    button.click()
                                    popup_found = True
                                    break
                        except:
                            continue
                        
                        if popup_found:
                            break
                    
                    if popup_found:
                        break
                        
                except:
                    pass
                
                time.sleep(0.5)
            
            if not popup_found:
                print("⚠️ Popup não encontrado, mas continuando...")
            
            # Aguarda o download
            time.sleep(3)
            
            # Verifica novos arquivos
            files_after = set(os.listdir(uc_folder)) if os.path.exists(uc_folder) else set()
            new_files = files_after - files_before
            
            # Procura por PDFs novos
            for new_file in new_files:
                if new_file.endswith('.pdf'):
                    old_path = os.path.join(uc_folder, new_file)
                    new_path = os.path.join(uc_folder, filename)
                    
                    if old_path != new_path:
                        os.rename(old_path, new_path)
                        print(f"✅ Arquivo renomeado: {new_file} → {filename}")
                    else:
                        print(f"✅ Download concluído: {filename}")
                    
                    return {
                        'mes': fatura_info['mes'],
                        'arquivo': filename,
                        'caminho': new_path,
                        'sucesso': True
                    }
            
            # Se não encontrou na pasta da UC, verifica Downloads padrão
            downloads_folder = os.path.join(os.path.expanduser("~"), "Downloads")
            download_path = self.wait_for_download_complete(downloads_folder, timeout=15)
            
            if download_path:
                # Move para a pasta correta
                import shutil
                new_path = os.path.join(uc_folder, filename)
                shutil.move(download_path, new_path)
                print(f"✅ Arquivo movido: {os.path.basename(download_path)} → {filename}")
                
                return {
                    'mes': fatura_info['mes'],
                    'arquivo': filename,
                    'caminho': new_path,
                    'sucesso': True
                }
            
            return {
                'mes': fatura_info['mes'],
                'arquivo': filename,
                'caminho': None,
                'sucesso': False
            }
            
        except Exception as e:
            print(f"❌ Erro no download: {e}")
            return {
                'mes': fatura_info.get('mes', 'Desconhecido'),
                'arquivo': None,
                'caminho': None,
                'sucesso': False,
                'erro': str(e)
            }   


#------------------------#
    def debug_page_elements(self):
        """Função para debug - mostra elementos da página"""
        try:
            print("\n🔧 DEBUG: Análise rápida da página")
            print(f"📍 URL: {self.driver.current_url}")
            print(f"📄 Título: {self.driver.title}")
            
            # Conta elementos principais
            inputs = self.driver.find_elements(By.TAG_NAME, "input")
            buttons = self.driver.find_elements(By.TAG_NAME, "button")
            forms = self.driver.find_elements(By.TAG_NAME, "form")
            
            print(f"📊 Resumo: {len(inputs)} inputs, {len(buttons)} buttons, {len(forms)} forms")
            
            # Salva HTML para análise detalhada
            try:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f'debug_page_{timestamp}.html'
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(self.driver.page_source)
                print(f"💾 HTML salvo em: {filename}")
            except Exception as e:
                print(f"❌ Erro ao salvar HTML: {e}")
                        
        except Exception as e:
            logger.error(f"Erro no debug: {e}")

    def perform_full_login(self, uc, cpf_cnpj, data_nascimento):
        """Executa o processo completo de login em etapas - VERSÃO SIMPLIFICADA"""
        try:
            print("\n🚀 INICIANDO PROCESSO DE LOGIN COMPLETO...")
            
            # Abre página de login
            if not self.open_login_page():
                return False
            
            # ETAPA 1: UC e CPF
            if not self.step1_fill_uc_cpf(uc, cpf_cnpj):
                return False
            
            if not self.step1_submit():
                return False
            
            # ETAPA 2: Data de nascimento
            if not self.step2_fill_birth_date(data_nascimento):
                return False
                
            if not self.step2_submit():
                return False
            
            # ETAPA 3: REMOVIDA - Não precisa mais tratar popup
            # A navegação direta para Segunda Via pula essa necessidade
            print("\n⏭️ Pulando etapa de popup - navegação direta implementada")
            
            # ETAPA 4: Navegar diretamente para Segunda Via
            if not self.step4_navigate_to_invoices():
                return False
            
            print("\n🎉 LOGIN COMPLETO REALIZADO COM SUCESSO!")
            print("📄 Você está na página de Segunda Via")
            self.logged_in = True
            return True
            
        except Exception as e:
            logger.error(f"Erro no processo completo de login: {e}")
            return False

    def close(self):
        """Fecha o navegador"""
        if self.driver:
            print("\n🔒 Fechando navegador...")
            self.driver.quit()

#------------------------#


#-------------- Main ----------#

def main():
    """Função principal"""
    print("=== Download de Faturas - Equatorial Goiás (Versão Corrigida) ===\n")
    
    # Tenta carregar credenciais do arquivo JSON
    credentials = load_credentials_from_json()
    
    # Pergunta sobre modo headless
    visual_mode = input("Deseja ver o processo no navegador? (s/N): ").strip().lower()
    headless = visual_mode not in ['s', 'sim', 'y', 'yes']
    
    if not headless:
        print("\n🌐 O navegador será aberto para você acompanhar o processo")
        print("👀 Deixe o navegador aberto durante toda a execução")
    
    # Coleta dados (se não vierem do JSON)
    if credentials:
        print("\n🔑 Credenciais carregadas do arquivo dados.json")
        uc = credentials["uc"]
        cpf_cnpj = credentials["cpf_cnpj"]
        data_nascimento = credentials["data_nascimento"]
        
        # Mostra dados (com mascara parcial)
        print(f"📋 UC: {uc}")
        print(f"📋 CPF/CNPJ: {cpf_cnpj[:3]}{'*' * (len(cpf_cnpj)-5)}{cpf_cnpj[-2:]}")
        print(f"📋 Data Nascimento: {data_nascimento}")
        
        # Confirmação de uso
        usar_json = input("\nDeseja usar estas credenciais? (S/n): ").strip().lower()
        if usar_json in ['', 's', 'sim', 'y', 'yes']:
            print("✅ Usando credenciais do arquivo JSON")
        else:
            credentials = None
    
    if not credentials:
        print("\n📋 DIGITE OS DADOS MANUALMENTE:")
        uc = input("Unidade Consumidora (UC): ").strip()
        cpf_cnpj = input("CPF/CNPJ: ").strip()
        data_nascimento = input("Data de nascimento (DD/MM/AAAA): ").strip()
    
    # Inicializa downloader
    downloader = EquatorialDownloaderFixed(headless=headless)
    
    try:
        # Configura driver
        if not downloader.setup_driver():
            return
        
        # Realiza login completo
        if downloader.perform_full_login(uc, cpf_cnpj, data_nascimento):
            print("\n✅ SUCESSO! Você está logado e na página de Segunda Via")
            
            # STEP 5 - Extração de UCs e criação da estrutura
            print("\n" + "="*60)
            print("🚀 INICIANDO STEP 5: EXTRAÇÃO DE DADOS...")
            print("="*60)
            
            if downloader.step5_extract_ucs_and_create_structure():
                print("\n✅ STEP 5 CONCLUÍDO COM SUCESSO!")
                print(f"📁 Pasta do cliente: {downloader.client_folder}")
                print(f"🔢 Total de UCs encontradas: {len(downloader.ucs_list)}")
                print(f"📄 Relatório JSON criado: {downloader.json_file_path}")
                
                # Mostra resumo das UCs encontradas
                print(f"\n🎯 DADOS EXTRAÍDOS:")
                print(f"   👤 Cliente: {downloader.client_name}")
                for i, uc in enumerate(downloader.ucs_list, 1):
                    print(f"   🔢 UC {i}: {uc}")
                
                # NOVO: Pergunta se deseja continuar para o Step 6
                continuar = input(f"\n⏳ Deseja continuar para o STEP 6 (processar {len(downloader.ucs_list)} UCs)? (s/N): ").strip().lower()
                
                if continuar in ['s', 'sim', 'y', 'yes']:
                    # STEP 6 - Processamento individual das UCs
                    print("\n" + "="*60)
                    print("🚀 INICIANDO STEP 6: PROCESSAMENTO DAS UCs...")
                    print("="*60)
                    
                    if downloader.step6_process_each_uc():
                        print("\n🎉 STEP 6 CONCLUÍDO COM SUCESSO!")
                        print("✅ Todas as UCs foram processadas individualmente")
                        
                        # Atualiza relatório final
                        downloader.update_final_report_after_step6()
                        
                        print(f"\n📊 RESUMO FINAL:")
                        print(f"   👤 Cliente: {downloader.client_name}")
                        print(f"   🔢 Total de UCs: {len(downloader.ucs_list)}")
                        print(f"   📁 Pasta: {downloader.client_folder}")
                        print(f"   📄 Relatório: {downloader.json_file_path}")
                        
                        
                        print("\n✅ PROCESSO COMPLETO!")
                        print(f"📊 Todas as faturas foram processadas e baixadas")
                        print(f"📁 Verifique os arquivos em: {downloader.client_folder}")
                        input("\nPressione Enter para finalizar...")
                                                    
                    else:
                        print("\n❌ ERRO no Step 6 - Falha no processamento das UCs")
                        print("🔧 Verifique os logs para mais detalhes")
                        input("Pressione Enter para finalizar...")
                else:
                    print("\n⏸️ Processo pausado após Step 5")
                    print(f"📁 Seus dados foram salvos em: {downloader.client_folder}")
                    input("Pressione Enter para finalizar...")
                    
            else:
                print("\n❌ ERRO no Step 5 - Não foi possível extrair as UCs")
                print("🔧 Verifique se você está na página correta de Segunda Via")
                input("Pressione Enter para continuar explorando manualmente ou fechar...")
                
        else:
            print("\n❌ Falha no login - verifique os dados e tente novamente")
            input("Pressione Enter para fechar...")
        
    except KeyboardInterrupt:
        print("\n\n⏹️ Programa interrompido pelo usuário")
        # Salva o que foi possível se o processo foi interrompido
        if hasattr(downloader, 'json_file_path') and downloader.json_file_path:
            print(f"💾 Dados parciais salvos em: {downloader.json_file_path}")
    except Exception as e:
        print(f"\n❌ Erro: {e}")
        logger.error(f"Erro não tratado: {e}")
        # Salva o que foi possível em caso de erro
        if hasattr(downloader, 'json_file_path') and downloader.json_file_path:
            print(f"💾 Tentando salvar dados parciais em: {downloader.json_file_path}")
    finally:
        downloader.close()

#-------------- Main ----------#


if __name__ == "__main__":
    main()