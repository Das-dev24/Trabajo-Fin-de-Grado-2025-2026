import os

CAL_BLANCO = "blanco"
CAL_OSCURO = "oscuro"

BAUDRATE    = 115200
WAVELENGTHS = [410, 435, 460, 485, 510, 535, 560, 585,
               610, 645, 680, 705, 730, 760, 810, 860, 900, 940]
CSV_HEADER  = ["A_410","B_435","C_460","D_485","E_510","F_535","G_560","H_585",
               "R_610","I_645","S_680","J_705","T_730","U_760","V_810","W_860",
               "K_900","L_940"]

_SRC_DIR = os.path.dirname(os.path.abspath(__file__))

DB_PATH = os.path.normpath(os.path.join(_SRC_DIR, '..', 'data', 'data.db'))
MODEL_PATH = os.path.normpath(os.path.join(_SRC_DIR, '..', 'models'))

MODO_REFLECTANCIA  = "reflectancia"
MODO_TRANSMITANCIA = "transmitancia"
