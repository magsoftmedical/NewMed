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
            "description": "Datos administrativos del paciente y de la consulta.",
            "properties": {
                "nombreCompleto": {
                    "type": "string",
                    "description": "Nombre completo del paciente."
                },
                "edad": {
                    "type": "object",
                    "description": "Edad del paciente expresada en años y meses.",
                    "properties": {
                        "anios": {
                            "type": ["integer", "null"],
                            "description": "Edad en años completos."
                        },
                        "meses": {
                            "type": ["integer", "null"],
                            "description": "Edad adicional en meses."
                        }
                    }
                },
                "sexo": {
                    "type": "string",
                    "enum": ["masculino", "femenino"],
                    "description": "Sexo biológico o género del paciente. Solo puede ser 'masculino' o 'femenino'."
                },
                "dni": {
                    "type": "string",
                    "description": "Documento nacional de identidad del paciente."
                },
                "grupoSangre": {
                    "type": "string",
                    "description": "Grupo sanguíneo del paciente (ejemplo: O+, A-)."
                },
                "fechaHora": {
                    "type": "string",
                    "description": "Fecha y hora de la consulta."
                },
                "seguro": {
                    "type": "string",
                    "description": "Entidad aseguradora del paciente."
                },
                "tipoConsulta": {
                    "type": "string",
                    "description": "Tipo de consulta (ejemplo: ambulatoria, emergencia, primera vez)."
                },
                "numeroSeguro": {
                    "type": "string",
                    "description": "Número de seguro o póliza del paciente."
                },
				"motivoConsulta": {
					"type": "string",
					"description": (
						"Razón principal por la cual el paciente consulta. "
						"Usualmente introducido con frases como 'acude para…' o 'el motivo de consulta es…'. "
						"Debe ser breve, una o dos frases máximo. "
						"Puede superponerse con sintomasPrincipales o relato."
					)
				},
            }
        },
        "anamnesis": {
            "type": "object",
            "description": "Historia clínica del paciente contada en la entrevista.",
            "properties": {
                "tiempoEnfermedad": {
                    "type": "string",
                    "description": "Tiempo de evolución de la enfermedad actual."
                },
                "sintomasPrincipales": {
					"type": "array",
					"items": {"type": "string"},
					"description": (
						"Lista breve de síntomas claves, cada uno de 1-3 palabras (ejemplo: 'fiebre', 'dolor abdominal'). "
						"Si el paciente menciona múltiples síntomas, dividirlos en elementos separados. "
						"Puede aparecer también en relato o motivoConsulta."
					)
				},
				"relato": {
					"type": "string",
					"description": (
						"Narrativa libre del paciente sobre su condición, en forma de oración o párrafo. "
						"Puede incluir los síntomas principales y el motivo, pero debe mantenerse como narración continua."
					)
				},
                "funcionesBiologicas": {
                    "type": "object",
                    "description": "Funciones biológicas básicas.",
                    "properties": {
                        "apetito": {"type": "string", "description": "Estado del apetito."},
                        "sed": {"type": "string", "description": "Estado de la sed."},
                        "orina": {"type": "string", "description": "Características de la orina."},
                        "deposiciones": {"type": "string", "description": "Características de las deposiciones."},
                        "sueno": {"type": "string", "description": "Calidad y cantidad del sueño."}
                    }
                },
                "antecedentes": {
                    "type": "object",
                    "description": "Antecedentes médicos del paciente y su familia.",
                    "properties": {
                        "personales": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Antecedentes médicos personales relevantes."
                        },
                        "padre": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Antecedentes médicos del padre."
                        },
                        "madre": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Antecedentes médicos de la madre."
                        }
                    }
                },
                "alergias": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Alergias conocidas del paciente."
                },
                "medicamentos": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Medicamentos que el paciente está tomando actualmente."
                }
            }
        },
        "examenClinico": {
            "type": "object",
            "description": "Hallazgos del examen clínico del paciente.",
            "properties": {
                "signosVitales": {
                    "type": "object",
                    "description": "Mediciones básicas de signos vitales.",
                    "properties": {
                        "PA": {"type": "string", "description": "Presión arterial (ejemplo: 120/80)."},
                        "FC": {"type": ["number", "null"], "description": "Frecuencia cardíaca (latidos por minuto)."},
                        "FR": {"type": ["number", "null"], "description": "Frecuencia respiratoria (respiraciones por minuto)."},
                        "temperatura": {"type": ["number", "null"], "description": "Temperatura corporal en °C."},
                        "SpO2": {"type": ["number", "null"], "description": "Saturación de oxígeno en % (ejemplo 98% o 98 por ciento)."},
                        "IMC": {"type": ["number", "null"], "description": "Índice de masa corporal."},
                        "peso": {"type": ["number", "null"], "description": "Peso en kilogramos."},
                        "talla": {"type": ["number", "null"], "description": "Talla en centímetros."},
                        "glasgow": {"type": ["number", "null"], "description": "Escala de coma de Glasgow."}
                    }
                },
                "estadoGeneral": {
                    "type": "string",
                    "description": "Descripción breve del estado general del paciente."
                },
                "descripcionGeneral": {
                    "type": "string",
                    "description": "Descripción detallada de los hallazgos clínicos generales."
                },
                "sistemas": {
                    "type": "object",
                    "description": "Examen físico por sistemas.",
                    "properties": {
                        "piel": {"type": "string", "description": "Hallazgos en la piel."},
                        "tcs": {"type": "string", "description": "Hallazgos en el tejido celular subcutáneo."},
                        "cabeza": {"type": "string", "description": "Hallazgos en cabeza."},
                        "cuello": {"type": "string", "description": "Hallazgos en cuello."},
                        "torax": {"type": "string", "description": "Hallazgos en tórax."},
                        "pulmones": {"type": "string", "description": "Hallazgos en pulmones."},
                        "corazon": {"type": "string", "description": "Hallazgos en corazón."},
                        "mamasAxilas": {"type": "string", "description": "Hallazgos en mamas y axilas."},
                        "abdomen": {"type": "string", "description": "Hallazgos en abdomen."},
                        "genitoUrinario": {"type": "string", "description": "Hallazgos en aparato genitourinario."},
                        "rectalPerianal": {"type": "string", "description": "Hallazgos en examen rectal y perianal."},
                        "extremidades": {"type": "string", "description": "Hallazgos en extremidades."},
                        "vascularPeriferico": {"type": "string", "description": "Hallazgos en sistema vascular periférico."},
                        "neurologico": {"type": "string", "description": "Hallazgos en examen neurológico."}
                    }
                }
            }
        },
        "diagnosticos": {
            "type": "array",
            "description": "Diagnósticos clínicos del paciente.",
            "items": {
                "type": "object",
                "properties": {
                    "nombre": {"type": "string", "description": "Nombre o etiqueta del diagnóstico."},
                    "tipo": {
                        "type": "string",
                        "enum": ["presuntivo", "definitivo"],
                        "description": "Tipo de diagnóstico: presuntivo o definitivo."
                    },
                    "cie10": {"type": "string", "description": "Código CIE-10 del diagnóstico."}
                }
            }
        },
        "tratamientos": {
            "type": "array",
            "description": "Tratamientos indicados al paciente.",
            "items": {
                "type": "object",
                "properties": {
                    "medicamento": {"type": "string", "description": "Nombre del medicamento o procedimiento."},
                    "dosisIndicacion": {"type": "string", "description": "Dosis o indicación de uso."},
                    "gtin": {"type": "string", "description": "Código GTIN o identificador del medicamento."}
                }
            }
        },
        "firma": {
            "type": "object",
            "description": "Datos de firma del médico responsable.",
            "properties": {
                "medico": {"type": "string", "description": "Nombre completo del médico."},
                "colegiatura": {"type": "string", "description": "Número de colegiatura del médico."},
                "fecha": {"type": "string", "description": "Fecha de firma."}
            }
        }
    }
}


# SCHEMA: Dict[str, Any] = {
# 	"type": "object",
# 	"properties": {
# 		"afiliacion": {
# 			"type": "object",
# 			"properties": {
# 				"nombreCompleto": {"type": "string"},
# 				"edad": {"type":"object","properties":{"anios":{"type":["integer","null"]},"meses":{"type":["integer","null"]}}},
# 				"sexo": {"type": "string"},
# 				"dni": {"type": "string"},
# 				"grupoSangre": {"type": "string"},
# 				"fechaHora": {"type": "string"},
# 				"seguro": {"type": "string"},
# 				"tipoConsulta": {"type": "string"},
# 				"numeroSeguro": {"type": "string"},
# 				"motivoConsulta": {"type": "string"}
# 			}
# 		},
# 		"anamnesis": {
# 			"type":"object",
# 			"properties":{
# 				"tiempoEnfermedad":{"type":"string"},
# 				"sintomasPrincipales":{"type":"array","items":{"type":"string"}},
# 				"relato":{"type":"string"},
# 				"funcionesBiologicas":{"type":"object","properties":{
# 					"apetito":{"type":"string"}, "sed":{"type":"string"}, "orina":{"type":"string"},
# 					"deposiciones":{"type":"string"}, "sueno":{"type":"string"}
# 				}},
# 				"antecedentes":{"type":"object","properties":{
# 					"personales":{"type":"array","items":{"type":"string"}},
# 					"padre":{"type":"array","items":{"type":"string"}},
# 					"madre":{"type":"array","items":{"type":"string"}}
# 				}},
# 				"alergias":{"type":"array","items":{"type":"string"}},
# 				"medicamentos":{"type":"array","items":{"type":"string"}}
# 			}
# 		},
# 		"examenClinico":{
# 			"type":"object",
# 			"properties":{
# 				"signosVitales":{"type":"object","properties":{
# 					"PA":{"type":"string"}, "FC":{"type":["number","null"]}, "FR":{"type":["number","null"]},
# 					"temperatura":{"type":["number","null"]}, "SpO2":{"type":["number","null"]},
# 					"IMC":{"type":["number","null"]}, "peso":{"type":["number","null"]},
# 					"talla":{"type":["number","null"]}, "glasgow":{"type":["number","null"]}
# 				}},
# 				"estadoGeneral":{"type":"string"},
# 				"descripcionGeneral":{"type":"string"},
# 				"sistemas":{"type":"object","properties":{
# 					"piel":{"type":"string"}, "tcs":{"type":"string"}, "cabeza":{"type":"string"},
# 					"cuello":{"type":"string"}, "torax":{"type":"string"}, "pulmones":{"type":"string"},
# 					"corazon":{"type":"string"}, "mamasAxilas":{"type":"string"}, "abdomen":{"type":"string"},
# 					"genitoUrinario":{"type":"string"}, "rectalPerianal":{"type":"string"},
# 					"extremidades":{"type":"string"}, "vascularPeriferico":{"type":"string"},
# 					"neurologico":{"type":"string"}
# 				}}
# 			}
# 		},
# 		"diagnosticos":{"type":"array","items":{
# 			"type":"object","properties":{
# 				"nombre":{"type":"string"},
# 				"tipo":{"type":"string","enum":["presuntivo","definitivo"]},
# 				"cie10":{"type":"string"}
# 			}
# 		}},
# 		"tratamientos":{"type":"array","items":{
# 			"type":"object","properties":{
# 				"medicamento":{"type":"string"},
# 				"dosisIndicacion":{"type":"string"},
# 				"gtin":{"type":"string"}
# 			}
# 		}},
# 		"firma":{"type":"object","properties":{
# 			"medico":{"type":"string"}, "colegiatura":{"type":"string"}, "fecha":{"type":"string"}
# 		}}
# 	}
# }

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

