from imports import *

def webdriver_setup():
    # Caminho para o ChromeDriver
    extension_path = r'c:\Users\aesouza\AppData\Local\Google\Chrome\User Data\Default\Extensions\dcngeagmmhegagicpcmpinaoklddcgon\2.17.0_0'
    # extension_path = r'c:\Users\Albano Souza\AppData\Local\Google\Chrome\User Data\Default\Extensions\dcngeagmmhegagicpcmpinaoklddcgon\2.17.0_0'
    chrome_options = Options()
    chrome_options.add_argument(f'--load-extension={extension_path}')


    #INICIALIZA DRIVER
    # driver = webdriver.Chrome(service=service, options=chrome_options)
    driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=chrome_options)
    wait = WebDriverWait(driver, 10, poll_frequency=2)  # Aguarda até 10 segundos
    return driver, wait