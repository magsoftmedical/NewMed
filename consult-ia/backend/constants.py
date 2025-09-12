from typing import Any, Dict

# Reglas mínimas que exigiremos (puedes ajustar)
REQUIRED_KEYS = [
    "afiliacion.motivoConsulta",
    "anamnesis.sintomasPrincipales",
    "diagnosticos",
    "tratamientos"
]

# ------------------ Schema de Historia Clínica (alineado a tu PDF) ------------------
SCHEMA: Dict[str, Any] = {
	"type": "object",
	"properties": {
		"afiliacion": {
			"type": "object",
			"properties": {
				"nombreCompleto": {"type": "string"},
				"edad": {"type":"object","properties":{"anios":{"type":["integer","null"]},"meses":{"type":["integer","null"]}}},
				"sexo": {"type": "string"},
				"dni": {"type": "string"},
				"grupoSangre": {"type": "string"},
				"fechaHora": {"type": "string"},
				"seguro": {"type": "string"},
				"tipoConsulta": {"type": "string"},
				"numeroSeguro": {"type": "string"},
				"motivoConsulta": {"type": "string"}
			}
		},
		"anamnesis": {
			"type":"object",
			"properties":{
				"tiempoEnfermedad":{"type":"string"},
				"sintomasPrincipales":{"type":"array","items":{"type":"string"}},
				"relato":{"type":"string"},
				"funcionesBiologicas":{"type":"object","properties":{
					"apetito":{"type":"string"}, "sed":{"type":"string"}, "orina":{"type":"string"},
					"deposiciones":{"type":"string"}, "sueno":{"type":"string"}
				}},
				"antecedentes":{"type":"object","properties":{
					"personales":{"type":"array","items":{"type":"string"}},
					"padre":{"type":"array","items":{"type":"string"}},
					"madre":{"type":"array","items":{"type":"string"}}
				}},
				"alergias":{"type":"array","items":{"type":"string"}},
				"medicamentos":{"type":"array","items":{"type":"string"}}
			}
		},
		"examenClinico":{
			"type":"object",
			"properties":{
				"signosVitales":{"type":"object","properties":{
					"PA":{"type":"string"}, "FC":{"type":["number","null"]}, "FR":{"type":["number","null"]},
					"temperatura":{"type":["number","null"]}, "SpO2":{"type":["number","null"]},
					"IMC":{"type":["number","null"]}, "peso":{"type":["number","null"]},
					"talla":{"type":["number","null"]}, "glasgow":{"type":["number","null"]}
				}},
				"estadoGeneral":{"type":"string"},
				"descripcionGeneral":{"type":"string"},
				"sistemas":{"type":"object","properties":{
					"piel":{"type":"string"}, "tcs":{"type":"string"}, "cabeza":{"type":"string"},
					"cuello":{"type":"string"}, "torax":{"type":"string"}, "pulmones":{"type":"string"},
					"corazon":{"type":"string"}, "mamasAxilas":{"type":"string"}, "abdomen":{"type":"string"},
					"genitoUrinario":{"type":"string"}, "rectalPerianal":{"type":"string"},
					"extremidades":{"type":"string"}, "vascularPeriferico":{"type":"string"},
					"neurologico":{"type":"string"}
				}}
			}
		},
		"diagnosticos":{"type":"array","items":{
			"type":"object","properties":{
				"nombre":{"type":"string"},
				"tipo":{"type":"string","enum":["presuntivo","definitivo"]},
				"cie10":{"type":"string"}
			}
		}},
		"tratamientos":{"type":"array","items":{
			"type":"object","properties":{
				"medicamento":{"type":"string"},
				"dosisIndicacion":{"type":"string"},
				"gtin":{"type":"string"}
			}
		}},
		"firma":{"type":"object","properties":{
			"medico":{"type":"string"}, "colegiatura":{"type":"string"}, "fecha":{"type":"string"}
		}}
	}
}

# SCHEMA: Dict[str, Any] = {
#     "type": "object",
#     "properties": {
#         "afiliacion": {
#             "type": "object",
#             "properties": {
#                 "nombreCompleto": {"type": "string"},
#                 "edad": {
#                     "type": "object",
#                     "properties": {"anios": {"type": "integer"}, "meses": {"type": "integer"}},
#                     "required": ["anios"],
#                     "additionalProperties": False
#                 },
#                 "sexo": {"type": "string", "enum": ["Masculino", "Femenino", "M", "F"]},
#                 "dni": {"type": "string"},
#                 "grupoSangre": {"type": "string"},
#                 "fechaHora": {"type": "string"},
#                 "seguro": {"type": "string"},
#                 "tipoConsulta": {"type": "string"},
#                 "numeroSeguro": {"type": "string"},
#                 "motivoConsulta": {"type": "string"}
#             },
#             "additionalProperties": False
#         },
#         "anamnesis": {
#             "type": "object",
#             "properties": {
#                 "tiempoEnfermedad": {"type": "string"},
#                 "sintomasPrincipales": {"type": "array", "items": {"type": "string"}},
#                 "relato": {"type": "string"},
#                 "funcionesBiologicas": {
#                     "type": "object",
#                     "properties": {
#                         "apetito": {"type": "string"},
#                         "sed": {"type": "string"},
#                         "orina": {"type": "string"},
#                         "deposiciones": {"type": "string"},
#                         "sueno": {"type": "string"}
#                     },
#                     "additionalProperties": False
#                 },
#                 "antecedentes": {
#                     "type": "object",
#                     "properties": {
#                         "personales": {"type": "array", "items": {"type": "string"}},
#                         "padre": {"type": "array", "items": {"type": "string"}},
#                         "madre": {"type": "array", "items": {"type": "string"}}
#                     },
#                     "additionalProperties": False
#                 },
#                 "alergias": {"type": "array", "items": {"type": "string"}},
#                 "medicamentos": {"type": "array", "items": {"type": "string"}}
#             },
#             "additionalProperties": False
#         },
#         "examenClinico": {
#             "type": "object",
#             "properties": {
#                 "signosVitales": {
#                     "type": "object",
#                     "properties": {
#                         "PA": {"type": "string"},
#                         "FC": {"type": "number"},
#                         "FR": {"type": "number"},
#                         "peso": {"type": "number"},
#                         "talla": {"type": "number"},
#                         "SpO2": {"type": "number"},
#                         "temperatura": {"type": "number"},
#                         "IMC": {"type": "number"},
#                         "glasgow": {"type": "number"}
#                     },
#                     "additionalProperties": False
#                 },
#                 "estadoGeneral": {"type": "string"},
#                 "descripcionGeneral": {"type": "string"},
#                 "sistemas": {
#                     "type": "object",
#                     "properties": {
#                         "piel": {"type": "string"},
#                         "tcs": {"type": "string"},
#                         "cabeza": {"type": "string"},
#                         "cuello": {"type": "string"},
#                         "torax": {"type": "string"},
#                         "pulmones": {"type": "string"},
#                         "corazon": {"type": "string"},
#                         "mamasAxilas": {"type": "string"},
#                         "abdomen": {"type": "string"},
#                         "genitoUrinario": {"type": "string"},
#                         "rectalPerianal": {"type": "string"},
#                         "extremidades": {"type": "string"},
#                         "vascularPeriferico": {"type": "string"},
#                         "neurologico": {"type": "string"}
#                     },
#                     "additionalProperties": False
#                 }
#             },
#             "additionalProperties": False
#         },
#         "diagnosticos": {
#             "type": "array",
#             "items": {
#                 "type": "object",
#                 "properties": {
#                     "nombre": {"type": "string"},
#                     "tipo": {"type": "string", "enum": ["presuntivo", "definitivo"]},
#                     "cie10": {"type": "string"}
#                 },
#                 "required": ["nombre"],
#                 "additionalProperties": False
#             }
#         },
#         "tratamientos": {
#             "type": "array",
#             "items": {
#                 "type": "object",
#                 "properties": {
#                     "medicamento": {"type": "string"},
#                     "dosisIndicacion": {"type": "string"},
#                     "gtin": {"type": "string"}
#                 },
#                 "required": ["medicamento"],
#                 "additionalProperties": False
#             }
#         },
#         "firma": {
#             "type": "object",
#             "properties": {
#                 "medico": {"type": "string"},
#                 "colegiatura": {"type": "string"},
#                 "fecha": {"type": "string"}
#             },
#             "additionalProperties": False
#         }
#     },
#     "additionalProperties": False
# }

