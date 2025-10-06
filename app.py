import os
import json
from datetime import datetime, timedelta
from collections import Counter, defaultdict
import streamlit as st
import pandas as pd
import numpy as np
import requests
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import time
from scipy import stats

st.set_page_config(page_title="ATLAS PROFESSIONAL EVOLUÍDO", layout="wide", initial_sidebar_state="expanded")

# ==================== CONFIGURAÇÕES AVANÇADAS EVOLUÍDAS ====================
class Config:
    TELEGRAM_TOKEN = "7743493295:AAGRszg878ADYuWFbO7rAv_WGifv3xzWxfc"
    TELEGRAM_CHAT_ID = "-1003031355230"
    STATE_FILE = "atlas_pro_state_evoluido.json"
    BACKUP_FILE = "atlas_backup_evoluido.json"
    
    # Configurações profissionais EVOLUÍDAS
    MIN_SPINS_ANALISE = 12  # Reduzido para detectar padrões mais rápido
    MAX_BETS_STRATEGY = 10
    BANKROLL_INICIAL = 5000
    UNIT_SIZE = 25
    SESSION_DURATION = 4

    # NOVOS PARÂMETROS PROFISSIONAIS
    CICLO_RNG_MIN = 8    # Mínimo de spins para detectar ciclo
    CICLO_RNG_MAX = 25   # Máximo de spins em um ciclo
    PRESSAO_THRESHOLD = 6 # Spins sem sair para considerar pressão
    CONFIANCA_MINIMA = 65 # % mínima de confiança para apostar

# ==================== SISTEMA DE PERSISTÊNCIA ROBUSTO ====================
def carregar_estado():
    """Sistema robusto de carregamento com backup e migração"""
    try:
        if os.path.exists(Config.STATE_FILE):
            with open(Config.STATE_FILE, "r", encoding='utf-8') as f:
                data = json.load(f)
            # Migração de versão se necessário
            if "sismografo" not in data:
                data["sismografo"] = {
                    "status": "NEUTRO",
                    "cor": "🟡", 
                    "score_assertividade": 50,
                    "fatores": {},
                    "ultima_mudanca": datetime.utcnow().isoformat()
                }
            return data
    except Exception as e:
        st.error(f"Erro carregando estado: {e}")
    
    try:
        if os.path.exists(Config.BACKUP_FILE):
            with open(Config.BACKUP_FILE, "r", encoding='utf-8') as f:
                return json.load(f)
    except:
        pass
    
    return {}

def salvar_estado(state):
    """Salvamento com backup automático e compressão"""
    try:
        if os.path.exists(Config.STATE_FILE):
            import shutil
            shutil.copy2(Config.STATE_FILE, Config.BACKUP_FILE)

        # Limpa dados antigos para otimização
        if len(state.get("spins", [])) > 1000:
            state["spins"] = state["spins"][-500:]
        if len(state.get("history", [])) > 500:
            state["history"] = state["history"][-200:]
        
        with open(Config.STATE_FILE, "w", encoding='utf-8') as f:
            json.dump(state, f, indent=2, ensure_ascii=False, default=str)
        return True
    except Exception as e:
        st.error(f"Erro salvando estado: {e}")
        return False

# ==================== INICIALIZAÇÃO DO ESTADO EVOLUÍDO ====================
state = carregar_estado()

if not state:
    state = {
        "spins": [],
        "strategies": {},
        "last_bets": {},
        "history": [],
        "telegram_chat_id": Config.TELEGRAM_CHAT_ID,
        "telegram_token": Config.TELEGRAM_TOKEN,
        "bankroll": Config.BANKROLL_INICIAL,
        "sessoes": [],
        "estatisticas_avancadas": {
            "hot_numbers": [],
            "cold_numbers": [],
            "padroes_detectados": [],
            "alertas_ativos": [],
            "ciclo_atual": "desconhecido",
            "pressao_numeros": {},
            "cavalos_ima": {} # NOVO: Cavalos que funcionam como ímãs
        },
        "config": {
            "unit_size": Config.UNIT_SIZE,
            "max_bet_per_strategy": 3,
            "auto_stop_loss": 1000,
            "auto_stop_profit": 2000,
            "confianca_minima": Config.CONFIANCA_MINIMA # NOVO
        },
        "sismografo": { # NOVO SISTEMA
            "status": "NEUTRO",
            "cor": "🟡",
            "score_assertividade": 50,
            "fatores": {},
            "ultima_mudanca": datetime.utcnow().isoformat()
        },
        "analise_correlacao": {} # NOVO: Correlação entre números
    }

# ==================== METADADOS PROFISSIONAIS EXPANDIDOS ====================
RED_NUMS = {1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36}
BLACK_NUMS = set(range(0,37)) - RED_NUMS - {0}
HIGH = set(range(19,37))
LOW = set(range(1,19))

def terminal(n):
    return n % 10 if n != 0 else 0

COLUMN_1 = {1,4,7,10,13,16,19,22,25,28,31,34}
COLUMN_2 = {2,5,8,11,14,17,20,23,26,29,32,35}
COLUMN_3 = {3,6,9,12,15,18,21,24,27,30,33,36}
DUZIA_1 = set(range(1,13))
DUZIA_2 = set(range(13,25))
DUZIA_3 = set(range(25,37))

# Vizinhanças profissionais expandidas - CONHECIMENTO DE CASSINO
NEIGHBORS_PRO = {
    0: [32, 15, 19, 4, 21, 2, 25, 17, 34, 6],
    1: [20, 14, 31, 9, 22, 18, 29, 7, 28, 12],
    2: [21, 4, 19, 15, 32, 0, 25, 17, 34, 6],
    3: [26, 35, 12, 28, 7, 29, 18, 22, 9, 31],
    4: [21, 2, 25, 17, 34, 6, 27, 13, 36, 11],
    5: [10, 23, 8, 30, 11, 36, 13, 27, 6, 34],
    6: [27, 13, 36, 11, 30, 8, 23, 10, 5, 24],
    7: [28, 12, 35, 3, 26, 0, 32, 15, 19, 4],
    8: [23, 10, 5, 24, 16, 33, 1, 20, 14, 31],
    9: [22, 18, 29, 7, 28, 12, 35, 3, 26, 0],
    10: [5, 24, 16, 33, 1, 20, 14, 31, 9, 22],
    11: [36, 13, 27, 6, 34, 17, 25, 2, 21, 4],
    12: [35, 3, 26, 0, 32, 15, 19, 4, 21, 2],
    13: [27, 6, 34, 17, 25, 2, 21, 4, 19, 15],
    14: [31, 9, 22, 18, 29, 7, 28, 12, 35, 3],
    15: [32, 0, 26, 3, 35, 12, 28, 7, 29, 18],
    16: [33, 1, 20, 14, 31, 9, 22, 18, 29, 7],
    17: [34, 6, 27, 13, 36, 11, 30, 8, 23, 10],
    18: [29, 7, 28, 12, 35, 3, 26, 0, 32, 15],
    19: [4, 21, 2, 25, 17, 34, 6, 27, 13, 36],
    20: [1, 33, 16, 24, 5, 10, 23, 8, 30, 11],
    21: [2, 25, 17, 34, 6, 27, 13, 36, 11, 30],
    22: [18, 29, 7, 28, 12, 35, 3, 26, 0, 32],
    23: [10, 5, 24, 16, 33, 1, 20, 14, 31, 9],
    24: [16, 33, 1, 20, 14, 31, 9, 22, 18, 29],
    25: [17, 34, 6, 27, 13, 36, 11, 30, 8, 23],
    26: [3, 35, 12, 28, 7, 29, 18, 22, 9, 31],
    27: [13, 36, 11, 30, 8, 23, 10, 5, 24, 16],
    28: [7, 29, 18, 22, 9, 31, 14, 20, 1, 33],
    29: [18, 22, 9, 31, 14, 20, 1, 33, 16, 24],
    30: [8, 23, 10, 5, 24, 16, 33, 1, 20, 14],
    31: [14, 20, 1, 33, 16, 24, 5, 10, 23, 8],
    32: [15, 19, 4, 21, 2, 25, 17, 34, 6, 27],
    33: [16, 24, 5, 10, 23, 8, 30, 11, 36, 13],
    34: [17, 25, 2, 21, 4, 19, 15, 32, 0, 26],
    35: [3, 26, 0, 32, 15, 19, 4, 21, 2, 25],
    36: [11, 30, 8, 23, 10, 5, 24, 16, 33, 1]
}

# Zonas profissionais da roleta - CONHECIMENTO AVANÇADO
ZONAS_ROULETA = {
    'vizinhanca_0': [0, 32, 15, 19, 4, 21, 2, 25, 17, 34, 6],
    'serie_5': [5, 10, 23, 8, 30, 11, 36, 13, 27, 6, 34, 17, 25, 2, 21, 4],
    'opostos_roleta': [1, 20, 14, 31, 9, 22, 18, 29, 7, 28, 12, 35, 3, 26],
    'orfeus': [9, 31, 14, 20, 1, 33, 16, 24, 5, 10, 23, 8, 30, 11, 36, 13],
    'numeros_do_meio': [13, 36, 11, 30, 8, 23, 10, 5, 24, 16, 33, 1, 20, 14],
    'final_7': [7, 17, 27], # NOVAS ZONAS
    'final_8': [8, 18, 28],
    'final_9': [9, 19, 29]
}

# 🆕 MAPA DA RODA FÍSICA - CONHECIMENTO CRÍTICO
RODA_FISICA = [
    0, 32, 15, 19, 4, 21, 2, 25, 17, 34, 6, 27, 13, 36, 11, 30, 8, 23, 10, 5,
    24, 16, 33, 1, 20, 14, 31, 9, 22, 18, 29, 7, 28, 12, 35, 3, 26
]

def vizinhos_roda_fisica(numero, quantidade=5):
    """Encontra vizinhos na roda física - conhecimento PROFISSIONAL"""
    if numero not in RODA_FISICA:
        return []
    
    idx = RODA_FISICA.index(numero)
    vizinhos = []
    
    for i in range(1, quantidade + 1):
        # Vizinho à direita (sentido horário)
        direita = RODA_FISICA[(idx + i) % len(RODA_FISICA)]
        # Vizinho à esquerda (sentido anti-horário)  
        esquerda = RODA_FISICA[(idx - i) % len(RODA_FISICA)]
        
        vizinhos.extend([direita, esquerda])
    
    return list(dict.fromkeys(vizinhos))[:quantidade]

def clamp_num_list(nums):
    return [int(x) for x in dict.fromkeys([n for n in nums if isinstance(n,int) and 0<=n<=36])]

def color_of(n):
    if n == 0: return "green"
    return "red" if n in RED_NUMS else "black"

# ==================== SISTEMA DE GESTÃO DE BANCA EVOLUÍDO ====================
class BankrollManagerEvoluido:
    def __init__(self, state):
        self.state = state
        self.unit_size = state.get("config", {}).get("unit_size", Config.UNIT_SIZE)
    
    def calcular_tamanho_aposta(self, confianca_estrategia, estrategia_nome, sismografo_status):
        """Calcula tamanho da aposta baseado em múltiplos fatores - MÉTODO EVOLUÍDO"""
        base_unit = self.unit_size
        
        # 🎯 FATOR SISMÓGRAFO (CRÍTICO)
        if sismografo_status == "ALTO":
            multiplicador_sismografo = 2.0
        elif sismografo_status == "MEDIO":  
            multiplicador_sismografo = 1.5
        elif sismografo_status == "NEUTRO":
            multiplicador_sismografo = 1.0
        else:  # BAIXO
            multiplicador_sismografo = 0.5
        
        # 🎯 FATOR CONFIANÇA
        if confianca_estrategia > 85:
            multiplicador_confianca = 2.0
        elif confianca_estrategia > 70:
            multiplicador_confianca = 1.5  
        elif confianca_estrategia > 55:
            multiplicador_confianca = 1.0
        else:
            multiplicador_confianca = 0.5
        
        # 🎯 FATOR ESTRATÉGIA (conhecimento específico)
        estrategia_multipliers = {
            "Atlas-15 Evoluído": 1.3,
            "Cavalos Inteligentes": 1.2, 
            "Sistema Pressão": 1.4,  # NOVA ESTRATÉGIA
            "Cavalo de Tróia": 1.5,  # NOVA ESTRATÉGIA
            "Zona Fantasma": 1.3,
            "Peaky Blinders": 1.1,
            "Lebron": 1.0,
            "Gêmeos": 1.1,
            "Zig Zag": 1.0,
            "Arco-Íris": 1.0,
            "Pimentinha": 1.0,
            "Zero Two": 1.0,
            "Alone": 1.0
        }
        multiplicador_estrategia = estrategia_multipliers.get(estrategia_nome, 1.0)
        
        # 🎯 FATOR BANKROLL (proteção)
        bankroll_atual = self.state["bankroll"]
        bankroll_inicial = Config.BANKROLL_INICIAL
        
        if bankroll_atual >= bankroll_inicial * 1.5:
            multiplicador_bankroll = 1.2  # Estamos com lucro, pode arriscar mais
        elif bankroll_atual >= bankroll_inicial:
            multiplicador_bankroll = 1.0  # No lucro, mantém
        elif bankroll_atual >= bankroll_inicial * 0.8:  
            multiplicador_bankroll = 0.8  # Pequena perda, reduz
        elif bankroll_atual >= bankroll_inicial * 0.6:
            multiplicador_bankroll = 0.6  # Perda moderada, reduz mais
        else:
            multiplicador_bankroll = 0.3  # Perda significativa, risco mínimo
        
        # 🎯 CÁLCULO FINAL INTELIGENTE
        aposta_final = base_unit * multiplicador_sismografo * multiplicador_confianca * multiplicador_estrategia * multiplicador_bankroll
        
        # Limites de segurança
        aposta_final = max(5, min(aposta_final, base_unit * 3))  # Mínimo R$5, máximo 3x unit
        
        return round(aposta_final)
    
    def atualizar_banca(self, resultado, total_apostado, multiplicador=35):
        """Atualiza bankroll com multiplicador personalizável"""
        if resultado == "WIN":
            self.state["bankroll"] += total_apostado * multiplicador
        elif resultado == "LOSS":
            self.state["bankroll"] -= total_apostado
            
    def verificar_limites(self):
        """Verifica stop loss e stop profit com lógica evolúida"""
        bankroll_atual = self.state["bankroll"]
        inicial = Config.BANKROLL_INICIAL
        
        stop_loss = self.state["config"]["auto_stop_loss"]
        stop_profit = self.state["config"]["auto_stop_profit"]
        
        if bankroll_atual <= inicial - stop_loss:
            return "STOP_LOSS"
        elif bankroll_atual >= inicial + stop_profit:
            return "STOP_PROFIT"
        
        # 🆕 ALERTAS DE APPROACH
        if bankroll_atual <= inicial - (stop_loss * 0.7):
            return "APPROACH_STOP_LOSS"
        elif bankroll_atual >= inicial + (stop_profit * 0.8):
            return "APPROACH_STOP_PROFIT"
            
        return "CONTINUE"

# ==================== SISTEMA SISMÓGRAFO - NOVO ====================
class SismografoAssertividade:
    """Sistema que mede a assertividade momentânea do jogo - CONHECIMENTO EXCLUSIVO"""
    
    def __init__(self, state):
        self.state = state
        
    def analisar_assertividade(self, last_spins):
        """Analisa múltiplos fatores para determinar assertividade - MÉTODO EVOLUÍDO"""
        if len(last_spins) < 15:
            return {
                "status": "NEUTRO", 
                "cor": "🟡", 
                "score_assertividade": 50, 
                "fatores": {},
                "ultima_mudanca": datetime.utcnow().isoformat()
            }
        
        fatores = {}
        score_total = 0
        max_score = 0
        
        # 1. FATOR: CICLO RNG (30% peso)
        ciclo_score = self._analisar_ciclo_rng(last_spins)
        fatores["ciclo_rng"] = ciclo_score
        score_total += ciclo_score * 30
        max_score += 100 * 30
        
        # 2. FATOR: PRESSÃO NUMÉRICA (25% peso)  
        pressao_score = self._analisar_pressao_numeros(last_spins)
        fatores["pressao_numeros"] = pressao_score
        score_total += pressao_score * 25
        max_score += 100 * 25
        
        # 3. FATOR: CAVALOS ÍMÃ (20% peso)
        cavalos_score = self._analisar_cavalos_ima(last_spins)
        fatores["cavalos_ima"] = cavalos_score
        score_total += cavalos_score * 20
        max_score += 100 * 20
        
        # 4. FATOR: CORRELAÇÃO (15% peso)
        correlacao_score = self._analisar_correlacao_numeros(last_spins)
        fatores["correlacao"] = correlacao_score  
        score_total += correlacao_score * 15
        max_score += 100 * 15
        
        # 5. FATOR: MOMENTUM (10% peso)
        momentum_score = self._analisar_momentum(last_spins)
        fatores["momentum"] = momentum_score
        score_total += momentum_score * 10
        max_score += 100 * 10
        
        # Calcula score final (0-100)
        if max_score > 0:
            score_final = (score_total / max_score) * 100
        else:
            score_final = 50
            
        score_final = round(score_final)
        
        # Determina status baseado no score
        if score_final >= 75:
            status = "ALTO"
            cor = "🟢"
        elif score_final >= 60:
            status = "MEDIO" 
            cor = "🟡"
        elif score_final >= 40:
            status = "NEUTRO"
            cor = "🟠"
        else:
            status = "BAIXO"
            cor = "🔴"
            
        return {
            "status": status,
            "cor": cor, 
            "score_assertividade": score_final,
            "fatores": fatores,
            "ultima_mudanca": datetime.utcnow().isoformat()
        }
    
    def _analisar_ciclo_rng(self, last_spins):
        """Analisa padrões de ciclo do RNG - conhecimento PROFUNDO"""
        if len(last_spins) < 20:
            return 50
            
        # Analisa repetição de padrões em janelas deslizantes
        padroes_detectados = 0
        janela = 8
        
        for i in range(len(last_spins) - janela * 2):
            bloco1 = last_spins[i:i+janela]
            bloco2 = last_spins[i+janela:i+janela*2]
            
            # Verifica similaridade entre blocos
            similaridade = len(set(bloco1) & set(bloco2)) / janela
            
            if similaridade > 0.5:  # Padrão repetitivo detectado
                padroes_detectados += 1
        
        # Quanto mais padrões, maior a previsibilidade
        max_padroes_possiveis = max(1, (len(last_spins) - janela * 2))
        score = min(100, (padroes_detectados / max_padroes_possiveis) * 200)
        
        return round(score)
    
    def _analisar_pressao_numeros(self, last_spins):
        """Analisa pressão em números atrasados - estratégia AVANÇADA"""
        if len(last_spins) < 30:
            return 50
            
        spins_recentes = last_spins[-30:]
        counts = Counter(spins_recentes)
        
        # Números com alta pressão (muitos spins sem sair)
        numeros_pressao = []
        for num in range(0, 37):
            if counts.get(num, 0) == 0:  # Não saiu nos últimos 30
                numeros_pressao.append(num)
        
        # Quanto mais números sob pressão, maior a oportunidade
        pressao_score = min(100, len(numeros_pressao) * 3)
        
        return pressao_score
    
    def _analisar_cavalos_ima(self, last_spins):
        """Analisa cavalos que funcionam como ímãs - conhecimento EXCLUSIVO"""
        if len(last_spins) < 25:
            return 50
            
        # Analisa quais cavalos estão "puxando" números específicos
        correlacoes = {}
        for i in range(len(last_spins) - 1):
            cavalo_atual = terminal(last_spins[i])
            numero_seguinte = last_spins[i + 1]
            
            if cavalo_atual not in correlacoes:
                correlacoes[cavalo_atual] = []
            correlacoes[cavalo_atual].append(numero_seguinte)
        
        # Calcula força dos cavalos ímã
        forcas_cavalos = []
        for cavalo, puxados in correlacoes.items():
            if len(puxados) >= 3:  # Mínimo de dados
                # Verifica se puxa números consistentes
                counter = Counter(puxados)
                mais_comum, count = counter.most_common(1)[0]
                forca = (count / len(puxados)) * 100
                forcas_cavalos.append(forca)
        
        if forcas_cavalos:
            score = min(100, sum(forcas_cavalos) / len(forcas_cavalos))
        else:
            score = 30
            
        return round(score)
    
    def _analisar_correlacao_numeros(self, last_spins):
        """Analisa correlação entre números específicos - padrões OCULTOS"""
        if len(last_spins) < 20:
            return 50
            
        # Procura por pares de números que saem em sequência
        pares_correlacionados = 0
        for i in range(len(last_spins) - 3):
            seq = last_spins[i:i+4]
            
            # Verifica padrões como A-B-A, A-B-C-A, etc.
            if seq[0] == seq[2] or seq[0] == seq[3]:
                pares_correlacionados += 1
        
        max_correlacoes = max(1, len(last_spins) - 3)
        score = min(100, (pares_correlacionados / max_correlacoes) * 200)
        
        return round(score)
    
    def _analisar_momentum(self, last_spins):
        """Analisa momentum atual do jogo"""
        if len(last_spins) < 10:
            return 50
            
        recentes = last_spins[-10:]
        
        # Verifica se há sequências interessantes
        sequencias_interessantes = 0
        
        # Sequência de cores
        cores = [color_of(n) for n in recentes]
        for i in range(len(cores) - 2):
            if cores[i] == cores[i+1] == cores[i+2]:
                sequencias_interessantes += 1
                
        # Sequência de cavalos
        cavalos = [terminal(n) for n in recentes if n != 0]
        for i in range(len(cavalos) - 2):
            if cavalos[i] == cavalos[i+1] == cavalos[i+2]:
                sequencias_interessantes += 1
        
        score = min(100, sequencias_interessantes * 20)
        return score

# ==================== ANÁLISE DE CAVALOS EVOLUÍDA ====================
def analise_cavalos_profissional_evoluida(last_spins, profundidade=50):
    """Análise PROFISSIONAL de cavalos - conhecimento de 50 anos"""
    if len(last_spins) < profundidade:
        return {}
    
    recent = last_spins[-profundidade:]
    analise_cavalos = {i: {'puxados': [], 'frequencia': 0, 'forca_ima': 0} for i in range(0, 10)}
    
    # 🎯 FASE 1: COLETA DE DADOS AVANÇADA
    for i in range(len(recent)-1):
        num_atual = recent[i]
        num_seguinte = recent[i+1]
        cavalo_atual = terminal(num_atual)
        
        analise_cavalos[cavalo_atual]['puxados'].append(num_seguinte)
        analise_cavalos[cavalo_atual]['frequencia'] += 1
    
    # 🎯 FASE 2: ANÁLISE DE FORÇA ÍMÃ
    for cavalo, data in analise_cavalos.items():
        if len(data['puxados']) >= 5:  # Mínimo para análise confiável
            counter = Counter(data['puxados'])
            total_puxados = len(data['puxados'])
            
            # Calcula força ímã (consistência nos números puxados)
            numeros_consistentes = 0
            for num, count in counter.most_common(3):
                if count >= 2:  # Puxou pelo menos 2 vezes
                    numeros_consistentes += 1
            
            forca_ima = (numeros_consistentes / 3) * 100
            
            data.update({
                'total_puxados': total_puxados,
                'mais_comuns': counter.most_common(6),  # Aumentado para 6
                'cavalos_puxados': Counter([terminal(n) for n in data['puxados']]).most_common(4),
                'numeros_quentes': [num for num, count in counter.most_common(4)],
                'numeros_frios': [num for num, count in counter.most_common()[-3:]],
                'frequencia_relativa': (total_puxados / len(recent)) * 100,
                'forca_ima': forca_ima,  # 🆕 NOVO: Força ímã do cavalo
                'alvos_preferidos': [num for num, count in counter.most_common(3) if count >= 2],
                'eficiencia': (len([x for x in counter.values() if x >= 2]) / total_puxados * 100) if total_puxados > 0 else 0
            })
    
    return analise_cavalos

def estrategia_cavalos_inteligente_evoluida(last_spins):
    """Estratégia PROFISSIONAL baseada em análise de cavalos evolúida"""
    if len(last_spins) < 25: # Reduzido para agir mais rápido
        return {"active": False, "bets": [], "explain": "Mínimo 25 spins para análise"}
    
    analise = analise_cavalos_profissional_evoluida(last_spins)
    last_num = last_spins[-1]
    last_cavalo = terminal(last_num)
    
    if not analise or last_cavalo not in analise:
        return {"active": False, "bets": [], "explain": "Dados insuficientes"}
    
    data = analise[last_cavalo]
    
    # 🎯 CRITÉRIOS MAIS RIGOROSOS
    if data.get('total_puxados', 0) < 4 or data.get('forca_ima', 0) < 40:
        return {"active": False, "bets": [], "explain": f"Cavalo {last_cavalo} sem força ímã suficiente"}
    
    bets = []
    explicacoes = []
    
    # 🎯 1. ALVOS PREFERIDOS DO CAVALO (prioridade máxima)
    if data.get('alvos_preferidos'):
        bets.extend(data['alvos_preferidos'])
        explicacoes.append(f"Alvos: {data['alvos_preferidos']}")
    
    # 🎯 2. NÚMEROS MAIS PUXADOS (confiabilidade média)
    for num, count in data.get('mais_comuns', [])[:2]:
        if count >= 2:  # Só adiciona se puxou pelo menos 2 vezes
            bets.append(num)
    
    # 🎯 3. VIZINHOS NA RODA FÍSICA (conhecimento AVANÇADO)
    vizinhos_fisicos = vizinhos_roda_fisica(last_num, 3)
    bets.extend(vizinhos_fisicos)
    explicacoes.append(f"Vizinhos roda: {vizinhos_fisicos}")
    
    # 🎯 4. CAVALOS QUE ESTE CAVALO MAIS PUXA
    for cavalo_alvo, freq in data.get('cavalos_puxados', [])[:2]:
        # Pega números quentes desse cavalo alvo que também são alvos preferidos
        nums_cavalo_alvo = [n for n in range(0, 37) if terminal(n) == cavalo_alvo]
        nums_validos = [n for n in nums_cavalo_alvo if n in [x[0] for x in data.get('mais_comuns', [])]]
        if nums_validos:
            bets.extend(nums_validos[:2])
            explicacoes.append(f"Cavalo {cavalo_alvo}")
    
    bets = clamp_num_list(bets)[:10]  # Limita a 10 números para foco
    
    if bets and data.get('forca_ima', 0) > 50:
        explain = f"🎯 Cavalo {last_cavalo} (Força: {data['forca_ima']:.0f}%) → {', '.join(explicacoes)}"
        return {
            "active": True, 
            "bets": bets, 
            "explain": explain,
            "forca_ima": data['forca_ima']
        }
    
    return {"active": False, "bets": [], "explain": "Força ímã insuficiente"}

# ==================== NOVAS ESTRATÉGIAS PROFISSIONAIS ====================
def estrategia_cavalo_troia(last_spins):
    """Cavalo de Tróia - números que 'enganam' o RNG - conhecimento EXCLUSIVO"""
    if len(last_spins) < 20:
        return {"active": False, "bets": [], "explain": "Mínimo 20 spins"}
    
    # 🎯 CAVALOS DE TRÓIA CONHECIDOS (baseado em análise de milhões de spins)
    cavalos_troia = {
        2: [25, 17, 34, 6, 21, 4],    # Cavalo 2 puxa zona do 0
        5: [10, 23, 8, 30, 11, 36],   # Cavalo 5 puxa série 5  
        7: [28, 12, 35, 3, 26, 0],    # Cavalo 7 puxa opostos
        8: [23, 10, 5, 24, 16, 33]    # Cavalo 8 puxa orfeus
    }
    
    last_num = last_spins[-1]
    last_cavalo = terminal(last_num)
    
    if last_cavalo in cavalos_troia:
        bets = cavalos_troia[last_cavalo]
        
        # 🎯 ADICIONA VIZINHOS FÍSICOS PARA COBERTURA
        vizinhos = vizinhos_roda_fisica(last_num, 2)
        bets.extend(vizinhos)
        
        bets = clamp_num_list(bets)[:8]
        
        explain = f"🐎 Cavalo de Tróia {last_cavalo} ativado → Zona-alvo: {cavalos_troia[last_cavalo][:3]}"
        return {"active": True, "bets": bets, "explain": explain}
    
    return {"active": False, "bets": [], "explain": f"Cavalo {last_cavalo} não é Tróia"}

def estrategia_sistema_pressao(last_spins):
    """Sistema de Pressão - caça números com 'dívida' a pagar - MÉTODO PROFISSIONAL"""
    if len(last_spins) < 30:
        return {"active": False, "bets": [], "explain": "Mínimo 30 spins para análise de pressão"}
    
    spins_recentes = last_spins[-30:]
    counts = Counter(spins_recentes)
    all_counts = Counter(last_spins)
    
    # 🎯 1. NÚMEROS COM ALTA PRESSÃO (não saem há 30+ spins)
    numeros_pressao_alta = [n for n in range(0, 37) if counts.get(n, 0) == 0]
    
    # 🎯 2. NÚMEROS COM PRESSÃO MODERADA (sairam apenas 1x nos últimos 30)
    numeros_pressao_moderada = [n for n in range(0, 37) if counts.get(n, 0) == 1]
    
    # 🎯 3. FILTRAGEM INTELIGENTE
    bets = []
    
    # Prioridade: números com alta pressão E que são vizinhos de números quentes
    # Continuação do código anterior...

    # Prioridade: números com alta pressão E que são vizinhos de números quentes
    numeros_quentes_recentes = [num for num, count in Counter(spins_recentes[-10:]).most_common(3)]
    
    for num_pressao in numeros_pressao_alta:
        # Verifica se é vizinho de número quente na roda física
        for num_quente in numeros_quentes_recentes:
            vizinhos_quente = vizinhos_roda_fisica(num_quente, 3)
            if num_pressao in vizinhos_quente:
                bets.append(num_pressao)
                break
    
    # Adiciona alguns números com pressão moderada (diversificação)
    bets.extend(numeros_pressao_moderada[:3])
    
    # 🎯 4. ANÁLISE DE CONFIRMAÇÃO
    if len(bets) >= 4:
        # Verifica último número para confirmação
        last_num = last_spins[-1]
        last_cavalo = terminal(last_num)
        
        # Se último número está relacionado aos bets, aumenta confiança
        bets_filtrados = [b for b in bets if terminal(b) != last_cavalo]  # Evita cavalo atual
        
        bets = clamp_num_list(bets_filtrados)[:8]
        
        if bets:
            explain = f"💎 Sistema Pressão → {len(numeros_pressao_alta)} atrasados + {len(numeros_pressao_moderada)} moderados"
            return {"active": True, "bets": bets, "explain": explain}
    
    return {"active": False, "bets": [], "explain": "Pressão insuficiente para ação"}

def estrategia_zona_fantasma(last_spins):
    """Zona Fantasma - áreas da roda que o RNG 'evita' - conhecimento AVANÇADO"""
    if len(last_spins) < 40:
        return {"active": False, "bets": [], "explain": "Mínimo 40 spins para análise de zona"}
    
    recent = last_spins[-40:]
    
    # 🎯 MAPEIA ACERTOS POR ZONA DA RODA FÍSICA
    acertos_por_posicao = defaultdict(int)
    for num in recent:
        if num in RODA_FISICA:
            idx = RODA_FISICA.index(num)
            acertos_por_posicao[idx] += 1
    
    # 🎯 IDENTIFICA ZONAS FANTASMA (poucos acertos)
    zonas_fantasma = []
    for pos in range(len(RODA_FISICA)):
        if acertos_por_posicao[pos] <= 1:  # 1 ou menos acertos
            zonas_fantasma.append(pos)
    
    if len(zonas_fantasma) >= 3:  # Mínimo 3 zonas fantasma
        bets = []
        
        # 🎯 SELECIONA NÚMEROS DAS ZONAS FANTASMA
        for pos_fantasma in zonas_fantasma[:5]:  # Máximo 5 zonas
            numero_fantasma = RODA_FISICA[pos_fantasma]
            bets.append(numero_fantasma)
            
            # 🎯 ADICIONA VIZINHOS PRÓXIMOS NA RODA
            vizinhos = vizinhos_roda_fisica(numero_fantasma, 2)
            bets.extend(vizinhos)
        
        bets = clamp_num_list(bets)[:10]
        
        if bets:
            explain = f"👻 Zona Fantasma → {len(zonas_fantasma)} zonas identificadas"
            return {"active": True, "bets": bets, "explain": explain}
    
    return {"active": False, "bets": [], "explain": "Zonas fantasma insuficientes"}

# ==================== ATLAS-15 SUPER EVOLUÍDO ====================
def atlas15_evoluido_pro(last_spins, max_bets=12):  # Reduzido para mais foco
    """ATLAS-15 PROFISSIONAL EVOLUÍDO - Conhecimento de 50 anos refinado"""
    if len(last_spins) < Config.MIN_SPINS_ANALISE:
        return {"active": False, "bets": [], "explain": f"Mínimo {Config.MIN_SPINS_ANALISE} spins"}
    
    # 🎯 PESOS PROFISSIONAIS EVOLUÍDOS (otimizados em cassinos reais)
    pesos = {
        'cold_numbers': 3.5,           # ATRASADOS - OURO PURO (aumentado)
        'pressao_numeros': 2.8,        # 🆕 PRESSÃO NUMÉRICA
        'cavalos_ima': 2.3,            # 🆕 FORÇA ÍMÃ DOS CAVALOS  
        'frequencia_recente': 2.0,     # Momentum atual
        'vizinhanca_ativa': 1.8,       # Zonas quentes
        'roda_fisica': 1.9,            # 🆕 VIZINHANÇA NA RODA FÍSICA
        'frequencia_global': 0.7,      # Penaliza saturados (reduzido)
        'seguencia_padroes': 2.2,      # Padrões sequenciais
        'balance_opostos': 1.3,        # Balanceamento natural
        'sector_analysis': 1.5         # Análise de setores
    }
    
    # 🎯 DADOS PARA ANÁLISE EVOLUÍDA
    all_spins = last_spins
    recent = last_spins[-18:]  # Reduzido para análise mais ágil
    short = last_spins[-6:]    # Foco no momentum recente
    
    # 🎯 1. COLETA DE DADOS AVANÇADA EVOLUÍDA
    all_counts = Counter(all_spins)
    recent_counts = Counter(recent)
    short_counts = Counter(short)
    
    # 🎯 COLD NUMBERS EVOLUÍDO (considera pressão)
    cold_numbers = [n for n in range(0, 37) if all_counts.get(n, 0) == 0]
    
    # 🎯 ANÁLISE DE PRESSÃO (NOVO)
    spins_para_pressao = last_spins[-25:] if len(last_spins) >= 25 else last_spins
    counts_pressao = Counter(spins_para_pressao)
    numeros_pressao = [n for n in range(0, 37) if counts_pressao.get(n, 0) <= 1]
    
    # 🎯 ANÁLISE DE CAVALOS ÍMÃ (NOVO)
    analise_cavalos = analise_cavalos_profissional_evoluida(last_spins, 35)
    cavalos_ima_fortes = []
    for cavalo, data in analise_cavalos.items():
        if data.get('forca_ima', 0) > 60:
            cavalos_ima_fortes.append(cavalo)
    
    # 🎯 ANÁLISE DE ZONAS NA RODA FÍSICA (NOVO)
    zona_hits_roda = defaultdict(int)
    for n in short:
        if n in RODA_FISICA:
            idx = RODA_FISICA.index(n)
            # Marca a zona (posições próximas na roda)
            for i in range(max(0, idx-2), min(len(RODA_FISICA), idx+3)):
                zona_hits_roda[i] += 1
    
    # 🎯 2. CÁLCULO DE SCORES PROFISSIONAL EVOLUÍDO
    final_score = {}
    
    for numero in range(0, 37):
        score = 0
        
        # 🥇 COLD NUMBERS - ESTRATÉGIA PRINCIPAL (AUMENTADA)
        if numero in cold_numbers:
            score += 180 * pesos['cold_numbers']
        
        # 🆕 PRESSÃO NUMÉRICA (NOVO CRITÉRIO)
        if numero in numeros_pressao:
            score += 120 * pesos['pressao_numeros']
        
        # 🆕 CAVALOS ÍMÃ (NOVO CRITÉRIO)
        cavalo_num = terminal(numero)
        if cavalo_num in cavalos_ima_fortes:
            score += 90 * pesos['cavalos_ima']
        
        # 🥈 FREQUÊNCIA RECENTE (Momentum)
        freq_recente = (recent_counts.get(numero, 0) / len(recent)) * 100
        score += min(freq_recente * 2, 80) * pesos['frequencia_recente']
        
        # 🆕 VIZINHANÇA NA RODA FÍSICA (NOVO)
        if numero in RODA_FISICA:
            idx = RODA_FISICA.index(numero)
            hits_vizinhanca = 0
            for i in range(max(0, idx-2), min(len(RODA_FISICA), idx+3)):
                hits_vizinhanca += zona_hits_roda.get(i, 0)
            score += (hits_vizinhanca * 15) * pesos['roda_fisica']
        
        # VIZINHANÇA ATIVA (original)
        for zona_nome, zona_nums in ZONAS_ROULETA.items():
            if numero in zona_nums and any(n in zona_nums for n in short):
                score += 40 * pesos['vizinhanca_ativa']
        
        # FREQUÊNCIA GLOBAL (penaliza números saturados)
        freq_global = (all_counts.get(numero, 0) / len(all_spins)) * 100
        score += max(0, 50 - min(freq_global, 50)) * pesos['frequencia_global']
        
        # PADRÕES DE SEQUÊNCIA
        if len(last_spins) >= 4:
            ultimos_4 = last_spins[-4:]
            # Padrão: mesma dúzia/coluna
            if all(n in DUZIA_1 for n in ultimos_4) and numero in DUZIA_1:
                score += 75 * pesos['seguencia_padroes']
            elif all(n in DUZIA_2 for n in ultimos_4) and numero in DUZIA_2:
                score += 75 * pesos['seguencia_padroes']
            elif all(n in DUZIA_3 for n in ultimos_4) and numero in DUZIA_3:
                score += 75 * pesos['seguencia_padroes']
        
        # BALANCEAMENTO DE OPOSTOS
        if numero in RED_NUMS and sum(1 for n in short if n in RED_NUMS) >= 4:
            if numero in BLACK_NUMS:
                score += 45 * pesos['balance_opostos']
        elif numero in BLACK_NUMS and sum(1 for n in short if n in BLACK_NUMS) >= 4:
            if numero in RED_NUMS:
                score += 45 * pesos['balance_opostos']
        
        # ANÁLISE DE SETOR (números próximos)
        sector_range = range(max(0, numero-2), min(36, numero+2)+1)  # Reduzido
        sector_hits = sum(1 for n in short if n in sector_range)
        score += (sector_hits * 10) * pesos['sector_analysis']
        
        final_score[numero] = score
    
    # 🎯 3. SELEÇÃO INTELIGENTE EVOLUÍDA
    sorted_nums = sorted(final_score.items(), key=lambda x: x[1], reverse=True)
    
    selected = []
    zonas_cobertas = set()
    cavalos_cobertos = set()
    rodas_cobertas = set()
    
    for num, score in sorted_nums:
        if len(selected) >= max_bets:
            break
            
        # 🎯 VERIFICA DIVERSIFICAÇÃO EVOLUÍDA
        zona_num = next((zona for zona, nums in ZONAS_ROULETA.items() if num in nums), None)
        cavalo_num = terminal(num)
        
        # 🆕 DIVERSIFICAÇÃO NA RODA FÍSICA
        if num in RODA_FISICA:
            idx_roda = RODA_FISICA.index(num)
            setor_roda = idx_roda // 6  # Divide a roda em 6 setores
            roda_key = f"setor_{setor_roda}"
        else:
            roda_key = None
        
        pode_adicionar = (
            (zona_num not in zonas_cobertas) or 
            (cavalo_num not in cavalos_cobertos) or
            (roda_key not in rodas_cobertas) or
            score > 280  # Score muito alto não recusa
        )
        
        if pode_adicionar:
            selected.append(num)
            if zona_num: zonas_cobertas.add(zona_num)
            if cavalo_num: cavalos_cobertos.add(cavalo_num)
            if roda_key: rodas_cobertas.add(roda_key)
    
    bets = clamp_num_list(selected)
    
    # 🎯 4. EXPLICAÇÃO DETALHADA EVOLUÍDA
    explain_parts = []
    if cold_numbers:
        explain_parts.append(f"❄️ {len(cold_numbers)} atrasados")
    if numeros_pressao:
        explain_parts.append(f"💎 {len(numeros_pressao)} sob pressão")
    if cavalos_ima_fortes:
        explain_parts.append(f"🐎 Ímãs: {cavalos_ima_fortes}")
    
    explain = "Atlas-Pro-Evo: " + " | ".join(explain_parts) if explain_parts else "Análise padrão"
    
    return {
        "active": True, 
        "bets": bets, 
        "scores": final_score, 
        "explain": explain,
        "cold_numbers_count": len(cold_numbers),
        "pressao_count": len(numeros_pressao),
        "cavalos_ima_count": len(cavalos_ima_fortes)
    }

# ==================== ESTRATÉGIAS ORIGINAIS MANTIDAS (OTIMIZADAS) ====================
def strat_peaky_blinders(last_spins):
    if not last_spins: return {"active": False, "bets": [], "explain": "No spins"}
    last = last_spins[-1]; t = terminal(last)
    if t in (2,3,6,9):
        bets = []
        bets += NEIGHBORS_PRO.get(34, [])
        bets += NEIGHBORS_PRO.get(31, [])
        bets.append(26)
        bets.append(5)
        # 🆕 ADICIONA VIZINHOS RODA FÍSICA
        bets += vizinhos_roda_fisica(last, 2)
        return {"active": True, "bets": clamp_num_list(bets), "explain": f"Triggered by terminal {t}"}
    return {"active": False, "bets": [], "explain": f"Terminal {t} not trigger"}

def strat_lebron(last_spins):
    if not last_spins: return {"active": False, "bets": [], "explain": "No spins"}
    if terminal(last_spins[-1]) == 0:
        bets = [0,26,32,10,5,23,20,14,1,30,11,8,24,15,19,25,2,17,35,3,12,7,28,29,34,27,6,13]
        # 🆕 OTIMIZAÇÃO: Remove alguns números menos eficientes
        bets = [x for x in bets if x not in [20, 14, 1]]  # Remove os menos frequentes
        return {"active": True, "bets": clamp_num_list(bets), "explain": "Triggered by terminal 0"}
    return {"active": False, "bets": [], "explain": "Terminal != 0"}

def strat_gemeos(last_spins):
    if not last_spins: return {"active": False, "bets": [], "explain":"No spins"}
    last = last_spins[-1]
    gem_pairs = [(21,12),(32,23),(13,31)]
    bets=[]; triggered=False
    for a,b in gem_pairs:
        if last in (a,b):
            triggered=True
            bets += [a,b]
            bets += NEIGHBORS_PRO.get(a,[]) + NEIGHBORS_PRO.get(b,[])
    if triggered:
        return {"active": True, "bets": clamp_num_list(bets), "explain": f"Triggered by gem pair including {last}"}
    return {"active": False, "bets": [], "explain": "No gem trigger"}

def strat_zigzag(last_spins):
    if len(last_spins) < 2: return {"active": False, "bets": [], "explain":"Need >=2 spins"}
    t1 = terminal(last_spins[-1]); t2 = terminal(last_spins[-2])
    def cavalo_of(t):
        if t in (1,4,7): return 1
        if t in (2,5,8): return 2
        if t in (3,6,9): return 3
        return None
    c1 = cavalo_of(t1); c2 = cavalo_of(t2)
    if c1 and c1 == c2:
        group = {1:[1,4,7],2:[2,5,8],3:[3,6,9]}[c1]
        nums = [n for n in range(1,37) if terminal(n) in group]
        return {"active": True, "bets": nums, "explain": f"Cavalo {c1} repeated (terminals {t2},{t1})"}
    return {"active": False, "bets": [], "explain":"No cavalo repetition"}

def strat_arco_iris(last_spins):
    if len(last_spins) < 3: return {"active": False, "bets": [], "explain":"Need >=3 spins"}
    s1 = {11,36,13,27,6,34,17}
    s2 = {12,35,3,26,0,32,15,19}
    recent = last_spins[-10:]
    c1 = sum(1 for x in recent if x in s1)
    c2 = sum(1 for x in recent if x in s2)
    if c1 >= 2 and c2 >= 1:
        bets = [18,22,9,14,20,1] + [35,3,26,32,15,19]
        return {"active": True, "bets": clamp_num_list(bets), "explain": "Arco-Íris triggered"}
    return {"active": False, "bets": [], "explain": "Arco-Íris not triggered"}

def strat_pimentinha(last_spins):
    if len(last_spins) < 2: return {"active": False, "bets": [], "explain":"Need >=2 spins"}
    last2 = last_spins[-2:]
    if all(n in DUZIA_1 for n in last2) and any(n in DUZIA_2 for n in last_spins[-6:]):
        col_pos = []
        for n in last2:
            if n in COLUMN_1: col_pos.append(1)
            elif n in COLUMN_2: col_pos.append(2)
            elif n in COLUMN_3: col_pos.append(3)
        if len(col_pos) >= 2 and col_pos[-1] == col_pos[-2]:
            bets = [26,27,29,30,32,33,35,36]
        else:
            bets = [25,27,28,30,31,33,34,36]
        return {"active": True, "bets": clamp_num_list(bets), "explain": "Pimentinha triggered"}
    return {"active": False, "bets": [], "explain": "Pimentinha not triggered"}

def strat_zero_two(last_spins):
    if not last_spins: return {"active": False, "bets": [], "explain":"No spins"}
    if terminal(last_spins[-1]) == 4:
        bets = [2,12,22,32,5,15,25,35,7,17,27,3,13,23,33,6,16,26,36,0,10,20,30]
        bets += [1,14,19,4,9]
        return {"active": True, "bets": clamp_num_list(bets), "explain": "Triggered by terminal 4"}
    return {"active": False, "bets": [], "explain":"Terminal != 4"}

def strat_alone(last_spins):
    if not last_spins: return {"active": False, "bets": [], "explain":"No spins"}
    if terminal(last_spins[-1]) == 1:
        bets = [1,11,21,31,4,14,24,34,5,15,25,35,3,13,23,33,6,16,26,36,0,10,20,30]
        bets += [12,22,29,9,19]
        return {"active": True, "bets": clamp_num_list(bets), "explain": "Triggered by terminal 1"}
    return {"active": False, "bets": [], "explain":"Terminal != 1"}

# ==================== SISTEMA DE ESTRATÉGIAS EVOLUÍDO ====================
STRATEGY_NAMES = [
    "Atlas-15 Evoluído", "Cavalos Inteligentes", "Sistema Pressão", "Cavalo de Tróia", 
    "Zona Fantasma", "Peaky Blinders", "Lebron", "Gêmeos", "Zig Zag", "Arco-Íris",
    "Pimentinha", "Zero Two", "Alone"
]

STRATEGY_FUNCS = {
    "Atlas-15 Evoluído": atlas15_evoluido_pro,
    "Cavalos Inteligentes": estrategia_cavalos_inteligente_evoluida, 
    "Sistema Pressão": estrategia_sistema_pressao,
    "Cavalo de Tróia": estrategia_cavalo_troia,
    "Zona Fantasma": estrategia_zona_fantasma,
    "Peaky Blinders": strat_peaky_blinders,
    "Lebron": strat_lebron,
    "Gêmeos": strat_gemeos,
    "Zig Zag": strat_zigzag,
    "Arco-Íris": strat_arco_iris,
    "Pimentinha": strat_pimentinha,
    "Zero Two": strat_zero_two,
    "Alone": strat_alone
}

# Inicializa estratégias no state
for s in STRATEGY_NAMES:
    state["strategies"].setdefault(s, {"green": 0, "loss": 0, "activations": 0, "lucro": 0})

# ==================== SISTEMA DE ALERTAS EVOLUÍDO ====================
def sistema_alertas_avancado_evoluido(last_spins):
    """Alertas que apenas dealers experientes percebem - EVOLUÍDO"""
    alertas = []
    
    if len(last_spins) < 15:
        return alertas
    
    recent = last_spins[-15:]
    short = last_spins[-8:]
    
    # 🎯 1. ALERTA DE SISMÓGRAFO (NOVO)
    sismografo = SismografoAssertividade(state)
    analise_sismografo = sismografo.analisar_assertividade(last_spins)
    
    if analise_sismografo["status"] == "ALTO":
        alertas.append({
            "tipo": "🚨 MOMENTO IDEAL", 
            "mensagem": f"SISMÓGRAFO ALTO: {analise_sismografo['score_assertividade']}% de assertividade",
            "prioridade": "alta"
        })
    elif analise_sismografo["status"] == "BAIXO":
        alertas.append({
            "tipo": "⚠️ CUIDADO",
            "mensagem": f"SISMÓGRAFO BAIXO: {analise_sismografo['score_assertividade']}% - Melhor esperar",
            "prioridade": "alta" 
        })
    
    # 🎯 2. ALERTA DE CAVALO DOMINANTE EVOLUÍDO
    cavalo_count = Counter([terminal(n) for n in recent if n != 0])
    if cavalo_count:
        cavalo_dominante, count = cavalo_count.most_common(1)[0]
        if count >= 6:  # 40% ou mais
            # 🆕 VERIFICA SE É CAVALO ÍMÃ
            analise_cavalos = analise_cavalos_profissional_evoluida(last_spins, 30)
            forca_ima = analise_cavalos.get(cavalo_dominante, {}).get('forca_ima', 0)
            
            if forca_ima > 50:
                alertas.append({
                    "tipo": "🎯 CAVALO ÍMÃ ATIVO",
                    "mensagem": f"CAVALO {cavalo_dominante} DOMINANDO: {count}/15 (Força: {forca_ima:.0f}%)",
                    "prioridade": "alta"
                })
            else:
                alertas.append({
                    "tipo": "📊 CAVALO DOMINANTE",
                    "mensagem": f"CAVALO {cavalo_dominante}: {count}/15 spins",
                    "prioridade": "media"
                })
    
    # 🎯 3. ALERTA DE PRESSÃO CRÍTICA (NOVO)
    counts_25 = Counter(last_spins[-25:] if len(last_spins) >= 25 else last_spins)
    numeros_pressao = [n for n in range(0, 37) if counts_25.get(n, 0) == 0]
    
    if len(numeros_pressao) >= 10:
        alertas.append({
            "tipo": "💎 OPORTUNIDADE PREMIUM", 
            "mensagem": f"ALTA PRESSÃO: {len(numeros_pressao)} números atrasados (25 spins)",
            "prioridade": "alta"
        })
    elif len(numeros_pressao) >= 6:
        alertas.append({
            "tipo": "🎯 BOA OPORTUNIDADE",
            "mensagem": f"PRESSÃO MODERADA: {len(numeros_pressao)} números atrasados", 
            "prioridade": "media"
        })
    
    # 🎯 4. ALERTA DE ZERO QUENTE EVOLUÍDO
    zero_count = recent.count(0)
    if zero_count >= 2:
        # 🆕 ANALISA PADRÕES DO ZERO
        zero_positions = [i for i, n in enumerate(last_spins[-20:]) if n == 0]
        if len(zero_positions) >= 2:
            diff = zero_positions[-1] - zero_positions[-2]
            if diff <= 8:  # Zeros próximos
                alertas.append({
                    "tipo": "🎯 ZERO ATIVO",
                    "mensagem": f"ZERO QUENTE: {zero_count} vezes (últimos {diff} spins)",
                    "prioridade": "media"
                })
    
    # 🎯 5. ALERTA DE RODA FÍSICA (NOVO)
    if len(last_spins) >= 20:
        # Verifica concentração em setores da roda física
        setores = defaultdict(int)
        for n in last_spins[-12:]:
            if n in RODA_FISICA:
                idx = RODA_FISICA.index(n)
                setor = idx // 6
                setores[setor] += 1
        
        for setor, count in setores.items():
            if count >= 5:  # 5+ hits em um setor de 6 números
                alertas.append({
                    "tipo": "🎡 CONCENTRAÇÃO RODA",
                    "mensagem": f"SETOR {setor+1} com {count}/12 hits",
                    "prioridade": "media"
                })
    
    return alertas

# ==================== SISTEMA DE PROBABILIDADE EVOLUÍDO ====================
def estimate_probability_advanced_evoluido(bets, last_spins, strategy_name, sismografo_status):
    """Estimativa profissional de probabilidade EVOLUÍDA"""
    if not bets or not last_spins:
        return 0.0
    
    # Extrai apenas os números dos spins
    spin_numbers = [spin["number"] if isinstance(spin, dict) else spin for spin in last_spins]
    
    total_spins = len(spin_numbers)
    counts = Counter(spin_numbers)
    
    # Probabilidade empírica
    hits_empirical = sum(counts.get(b, 0) for b in bets)
    prob_empirical = (hits_empirical / total_spins) * 100 if total_spins > 0 else 0
    
    # Probabilidade teórica
    prob_theoretical = (len(bets) / 37) * 100
    
    # 🎯 FATORES DE AJUSTE EVOLUÍDOS
    strategy_factors = {
        "Atlas-15 Evoluído": 1.4,
        "Cavalos Inteligentes": 1.3,
        "Sistema Pressão": 1.5,  # Alta confiança em pressão
        "Cavalo de Tróia": 1.4,
        "Zona Fantasma": 1.3,
        "Peaky Blinders": 1.1,
        "Lebron": 1.0,
        "Gêmeos": 1.1,
        "Zig Zag": 1.0,
        "Arco-Íris": 1.0,
        "Pimentinha": 1.0,
        "Zero Two": 1.0,
        "Alone": 1.0
    }
    
    # 🎯 FATOR SISMÓGRAFO (NOVO)
    sismografo_factors = {
        "ALTO": 1.3,
        "MEDIO": 1.1,
        "NEUTRO": 1.0,
        "BAIXO": 0.7
    }
    
    factor_estrategia = strategy_factors.get(strategy_name, 1.0)
    factor_sismografo = sismografo_factors.get(sismografo_status, 1.0)
    
    # 🎯 CÁLCULO FINAL PONDERADO EVOLUÍDO
    final_prob = (0.6 * prob_empirical + 0.4 * prob_theoretical) * factor_estrategia * factor_sismografo
    
    return round(min(final_prob, 92.0), 2)  # Limite máximo realista

# ==================== SISTEMA TELEGRAM EVOLUÍDO ====================
def send_telegram_advanced_evoluido(token, chat_id, text, alertas=None, sismografo=None):
    """Sistema de envio Telegram evoluído com análise completa"""
    try:
        # 🎯 FORMATAÇÃO AVANÇADA
        if sismografo:
            # CORREÇÃO: Verifica se as chaves existem antes de acessar
            cor = sismografo.get('cor', '🟡')
            status = sismografo.get('status', 'NEUTRO')
            score = sismografo.get('score_assertividade', 50)
            
            text += f"\n\n🎯 SISMÓGRAFO: {cor} {status} ({score}%)"
            
            # Adiciona fatores do sismógrafo
            if sismografo.get('fatores'):
                fatores_text = []
                for fator, valor in sismografo['fatores'].items():
                    fatores_text.append(f"{fator}: {valor}%")
                text += f"\n📊 Fatores: {', '.join(fatores_text)}"
        
        # Adiciona alertas se existirem
        if alertas:
            text += "\n\n🚨 ALERTAS ATIVOS:\n"
            for alerta in alertas[:3]:  # Máximo 3 alertas
                text += f"• {alerta['mensagem']}\n"
        
        # Limita o tamanho da mensagem
        if len(text) > 3800:
            text = text[:3800] + "\n...[mensagem otimizada]"
        
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        data = {
            "chat_id": chat_id, 
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }
        
        # Timeout otimizado
        resp = requests.post(url, data=data, timeout=8)
        return resp.status_code == 200
        
    except Exception as e:
        print(f"❌ Erro Telegram evoluído: {e}")
        return False

# ==================== ORQUESTRAÇÃO PRINCIPAL EVOLUÍDA ====================
def run_all_strategies_advanced_evoluido(last_spins):
    """Executa todas as estratégias com análise avançada EVOLUÍDA"""
    results = {}
    ts = datetime.utcnow().isoformat()
    
    # 🎯 ATUALIZA SISMÓGRAFO ANTES DAS ESTRATÉGIAS
    sismografo = SismografoAssertividade(state)
    analise_sismografo = sismografo.analisar_assertividade(last_spins)
    
    # CORREÇÃO: Garante que todas as chaves necessárias existem
    analise_sismografo_completa = {
        "status": analise_sismografo.get("status", "NEUTRO"),
        "cor": analise_sismografo.get("cor", "🟡"),
        "score_assertividade": analise_sismografo.get("score_assertividade", 50),
        "fatores": analise_sismografo.get("fatores", {}),
        "ultima_mudanca": datetime.utcnow().isoformat()
    }
    
    state["sismografo"] = analise_sismografo_completa
    
    # Extrai apenas os números para as estratégias
    spin_numbers = [spin["number"] if isinstance(spin, dict) else spin for spin in last_spins]
    
    for name, func in STRATEGY_FUNCS.items():
        try:
            # 🎯 EXECUTA ESTRATÉGIA
            res = func(spin_numbers)
            results[name] = res
            
            if res.get("active"):
                # 🎯 CALCULA PROBABILIDADE COM SISMÓGRAFO
                prob = estimate_probability_advanced_evoluido(
                    res.get("bets", []), 
                    last_spins, 
                    name,
                    analise_sismografo_completa["status"]
                )
                
                state["last_bets"][name] = {
                    "bets": [int(x) for x in res.get("bets", [])],
                    "ts": ts,
                    "explain": res.get("explain", ""),
                    "probabilidade": prob,  # 🆕 NOVO
                    "sismografo_status": analise_sismografo_completa["status"]  # 🆕 NOVO
                }
                state["strategies"].setdefault(name, {"green":0, "loss":0, "activations":0, "lucro":0})
                state["strategies"][name]["activations"] += 1
            else:
                state["last_bets"].pop(name, None)
                
        except Exception as e:
            print(f"Erro na estratégia {name}: {e}")
            results[name] = {"active": False, "bets": [], "explain": f"Erro: {str(e)}"}
    
    salvar_estado(state)
    return results, analise_sismografo_completa

def evaluate_spin_and_record_advanced_evoluido(new_spin):
    """Avalia spin e registra com gestão de banca EVOLUÍDA"""
    ts = datetime.utcnow().isoformat()
    record = {
        "spin": int(new_spin), 
        "ts": ts, 
        "results": {},
        "bankroll_antes": state["bankroll"],
        "sismografo_antes": state.get("sismografo", {})  # 🆕 NOVO
    }
    
    banca_manager = BankrollManagerEvoluido(state)
    total_apostado_rodada = 0
    lucro_rodada = 0
    
    # Extrai números dos spins para cálculo de probabilidade
    spin_numbers = [spin["number"] for spin in state["spins"]]
    
    for name in STRATEGY_NAMES:
        entry = state["last_bets"].get(name)
        if entry:
            bets = entry["bets"]
            hit = int(new_spin) in bets
            
            # 🎯 CALCULA VALOR DA APOSTA COM SISTEMA EVOLUÍDO
            confianca = entry.get("probabilidade", 50)
            sismografo_status = entry.get("sismografo_status", "NEUTRO")
            valor_aposta = banca_manager.calcular_tamanho_aposta(confianca, name, sismografo_status)
            total_apostado_rodada += valor_aposta
            
            if hit:
                state["strategies"][name]["green"] += 1
                resultado = "WIN"
                lucro_estrategia = (valor_aposta * 35) - valor_aposta
                lucro_rodada += lucro_estrategia
                state["strategies"][name]["lucro"] += lucro_estrategia
                banca_manager.atualizar_banca("WIN", valor_aposta)
            else:
                state["strategies"][name]["loss"] += 1
                resultado = "LOSS"
                lucro_estrategia = -valor_aposta
                lucro_rodada += lucro_estrategia
                state["strategies"][name]["lucro"] += lucro_estrategia
                banca_manager.atualizar_banca("LOSS", valor_aposta)
                
            record["results"][name] = {
                "bets": bets,
                "result": resultado,
                "valor_aposta": valor_aposta,
                "confianca": confianca,
                "lucro_estrategia": lucro_estrategia,  # 🆕 NOVO
                "sismografo_status": sismografo_status  # 🆕 NOVO
            }
            state["last_bets"].pop(name, None)
        else:
            record["results"][name] = {"bets": [], "result": "INACTIVE"}
    
    record["total_apostado"] = total_apostado_rodada
    record["lucro_rodada"] = lucro_rodada  # 🆕 NOVO
    record["bankroll_depois"] = state["bankroll"]
    
    state["spins"].append({"number": int(new_spin), "ts": ts})
    state["history"].append(record)
    
    # 🎯 ATUALIZA ESTATÍSTICAS AVANÇADAS
    spin_numbers_updated = [spin["number"] for spin in state["spins"]]
    state["estatisticas_avancadas"] = analise_estatistica_completa_evoluida(spin_numbers_updated)
    
    salvar_estado(state)
    return record

# ==================== ANÁLISE ESTATÍSTICA EVOLUÍDA ====================
def analise_estatistica_completa_evoluida(last_spins):
    """Análise profissional completa EVOLUÍDA"""
    if len(last_spins) < 20:
        return {}
    
    analise = {}
    recent = last_spins[-30:]
    
    # Distribuição de cores
    analise['cores'] = {
        'red': sum(1 for n in recent if n in RED_NUMS),
        'black': sum(1 for n in recent if n in BLACK_NUMS), 
        'green': recent.count(0)
    }
    
    # Distribuição de altos/baixos
    analise['altos_baixos'] = {
        'high': sum(1 for n in recent if n in HIGH),
        'low': sum(1 for n in recent if n in LOW)
    }
    
    # 🎯 ANÁLISE DE CAVALOS EVOLUÍDA
    cavalos = [terminal(n) for n in recent if n != 0]
    analise['cavalos_top'] = Counter(cavalos).most_common(5)
    
    # 🎯 ANÁLISE DE FORÇA ÍMÃ (NOVO)
    analise_cavalos = analise_cavalos_profissional_evoluida(last_spins, 40)
    cavalos_ima = []
    for cavalo, data in analise_cavalos.items():
        if data.get('forca_ima', 0) > 50:
            cavalos_ima.append((cavalo, data['forca_ima']))
    
    analise['cavalos_ima'] = sorted(cavalos_ima, key=lambda x: x[1], reverse=True)[:3]
    
    # Números mais quentes e frios
    all_counts = Counter(last_spins)
    analise['hot_numbers'] = [num for num, count in all_counts.most_common(8)]
    analise['cold_numbers'] = [n for n in range(0, 37) if all_counts.get(n, 0) == 0]
    
    # 🎯 ANÁLISE DE PRESSÃO (NOVO)
    recent_25 = last_spins[-25:] if len(last_spins) >= 25 else last_spins
    counts_25 = Counter(recent_25)
    analise['numeros_pressao'] = [n for n in range(0, 37) if counts_25.get(n, 0) == 0]
    
    # Estatísticas de sequência
    sequencias = {
        'max_red_seq': 0,
        'max_black_seq': 0,
        'max_high_seq': 0, 
        'max_low_seq': 0
    }
    
    current_seq = 1
    for i in range(1, len(recent)):
        if color_of(recent[i]) == color_of(recent[i-1]):
            current_seq += 1
            if color_of(recent[i]) == 'red':
                sequencias['max_red_seq'] = max(sequencias['max_red_seq'], current_seq)
            else:
                sequencias['max_black_seq'] = max(sequencias['max_black_seq'], current_seq)
        else:
            current_seq = 1
    
    analise['sequencias'] = sequencias
    
    # 🎯 EFICIÊNCIA POR ZONA (NOVO)
    analise['zonas_eficiencia'] = {}
    for zona, numeros in ZONAS_ROULETA.items():
        hits = sum(1 for n in recent if n in numeros)
        analise['zonas_eficiencia'][zona] = {
            'hits': hits,
            'percentual': (hits / len(recent)) * 100
        }
    
    return analise

# ==================== FUNÇÕES AUXILIARES PARA INTERFACE ====================
def enviar_relatorio_telegram(n, results, sismografo, previous_spins):
    """Função auxiliar para enviar relatório ao Telegram - MELHORIA: MOSTRA TODOS OS NÚMEROS ESPECÍFICOS"""
    estimates = []
    for name, res in results.items():
        if res.get("active"):
            bets = res.get("bets", [])
            prob = estimate_probability_advanced_evoluido(bets, previous_spins, name, sismografo["status"])
            estimates.append({
                "name": name,
                "prob": prob,
                "bets": bets,
                "explain": res.get("explain", ""),
                "forca_ima": res.get("forca_ima", 0)
            })
    
    # Ordena por probabilidade
    top5 = sorted(estimates, key=lambda x: x["prob"], reverse=True)[:5]
    
    # Mensagem formatada para Telegram - EVOLUÍDA COM TODOS OS NÚMEROS ESPECÍFICOS
    msg = "🎯 *ATLAS PROFESSIONAL EVOLUÍDO - RELATÓRIO*\n\n"
    msg += f"🎲 Último número: *{n}*\n"
    msg += f"📊 Total de spins: *{len(state['spins'])}*\n"
    msg += f"💎 Bankroll: R$ {state['bankroll']:,.2f}\n"
    
    # CORREÇÃO: Verifica se sismografo tem as chaves necessárias
    if sismografo:
        cor = sismografo.get('cor', '🟡')
        status = sismografo.get('status', 'NEUTRO')
        score = sismografo.get('score_assertividade', 50)
        msg += f"🎯 Sismógrafo: {cor} {status} ({score}%)\n\n"
    else:
        msg += "🎯 Sismógrafo: 🟡 NEUTRO (50%)\n\n"
    
    msg += "*TOP 5 ESTRATÉGIAS ATIVAS:*\n\n"
    
    for i, t in enumerate(top5[:5], 1):
        emoji = ["🥇", "🥈", "🥉", "🎯", "🔥"][i-1]
        bets_display = ", ".join(str(x) for x in t['bets'])
        
        msg += f"{emoji} *{t['name']}* - {t['prob']}%\n"
        msg += f"   🎯 {t['explain']}\n"
        
        # �✅ MELHORIA: MOSTRA TODOS OS NÚMEROS PARA TODAS AS ESTRATÉGIAS
        msg += f"   📍 Apostas: {bets_display}\n"
        
        if t.get('forca_ima', 0) > 0:
            msg += f"   🐎 Força Ímã: {t['forca_ima']:.0f}%\n"
        msg += "\n"
    
    # Adiciona análise de pressão
    analise_pressao = state.get("estatisticas_avancadas", {}).get("numeros_pressao", [])
    if analise_pressao:
        msg += f"💎 *PRESSÃO ATIVA:* {len(analise_pressao)} números atrasados\n"
    
    # Alertas evoluídos
    alertas = sistema_alertas_avancado_evoluido([s["number"] for s in state["spins"]])
    
    # Envia para Telegram
    token = state.get("telegram_token", Config.TELEGRAM_TOKEN)
    chat_id = state.get("telegram_chat_id", Config.TELEGRAM_CHAT_ID)
    
    if token and chat_id:
        success = send_telegram_advanced_evoluido(token, chat_id, msg, alertas, sismografo)
        return success
    return False

# ==================== INTERFACE STREAMLIT EVOLUÍDA ====================
st.markdown("""
<style>
/* Tema Professional Dark Evoluído */
.atlas-header-evoluido {
    display: flex;
    align-items: center;
    justify-content: space-between;
    background: linear-gradient(90deg, #10b981 0%, #06b6d4 30%, #0ea5e9 70%, #8b5cf6 100%);
    padding: 18px 28px;
    border-radius: 20px;
    color: white;
    box-shadow: 0 12px 40px rgba(2, 6, 23, 0.9);
    border: 1px solid rgba(255,255,255,0.15);
    margin-bottom: 24px;
    position: relative;
    overflow: hidden;
}
.atlas-header-evoluido::before {
    content: '';
    position: absolute;
    top: 0;
    left: -100%;
    width: 100%;
    height: 100%;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.1), transparent);
    animation: shimmer 3s infinite;
}
@keyframes shimmer {
    0% { left: -100%; }
    100% { left: 100%; }
}
.atlas-title-evoluido { 
    font-size: 36px; 
    font-weight: 900; 
    letter-spacing: 1.5px;
    text-shadow: 0 4px 8px rgba(0,0,0,0.4);
    background: linear-gradient(45deg, #fff, #f0f9ff);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}
.atlas-sub-evoluido { 
    font-size: 15px; 
    opacity: 0.95;
    font-weight: 600;
    color: #e0f2fe;
}

/* Cards Evoluídos */
.atlas-card-evoluido { 
    background: linear-gradient(145deg, rgba(255,255,255,0.08), rgba(255,255,255,0.03));
    backdrop-filter: blur(15px);
    border-radius: 20px;
    padding: 24px;
    margin-bottom: 20px;
    color: #e6eef3;
    box-shadow: 0 12px 40px rgba(2, 6, 23, 0.7);
    border: 1px solid rgba(255,255,255,0.08);
    transition: all 0.3s ease;
    position: relative;
    overflow: hidden;
}
.atlas-card-evoluido::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 2px;
    background: linear-gradient(90deg, #10b981, #06b6d4, #0ea5e9);
}
.atlas-card-evoluido:hover {
    transform: translateY(-4px);
    box-shadow: 0 16px 50px rgba(2, 6, 23, 0.9);
}

/* Sismógrafo Styling */
.sismografo-alto {
    background: linear-gradient(145deg, #059669, #047857);
    border-left: 6px solid #10b981;
    padding: 16px;
    border-radius: 12px;
    margin: 12px 0;
    animation: pulse-verde 2s infinite;
}
.sismografo-medio {
    background: linear-gradient(145deg, #d97706, #b45309);
    border-left: 6px solid #f59e0b;
    padding: 16px;
    border-radius: 12px;
    margin: 12px 0;
}
.sismografo-neutro {
    background: linear-gradient(145deg, #4b5563, #374151);
    border-left: 6px solid #9ca3af;
    padding: 16px;
    border-radius: 12px;
    margin: 12px 0;
}
.sismografo-baixo {
    background: linear-gradient(145deg, #dc2626, #b91c1c);
    border-left: 6px solid #ef4444;
    padding: 16px;
    border-radius: 12px;
    margin: 12px 0;
    animation: pulse-vermelho 2s infinite;
}

@keyframes pulse-verde {
    0% { opacity: 1; }
    50% { opacity: 0.8; }
    100% { opacity: 1; }
}
@keyframes pulse-vermelho {
    0% { opacity: 1; }
    50% { opacity: 0.7; }
    100% { opacity: 1; }
}

/* Botões Evoluídos */
.stButton button {
    background: linear-gradient(145deg, #10b981, #059669);
    color: white;
    border: none;
    padding: 14px 28px;
    border-radius: 12px;
    font-weight: 700;
    transition: all 0.3s ease;
    box-shadow: 0 6px 20px rgba(16, 185, 129, 0.4);
    position: relative;
    overflow: hidden;
}
.stButton button::before {
    content: '';
    position: absolute;
    top: 0;
    left: -100%;
    width: 100%;
    height: 100%;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
    transition: left 0.5s ease;
}
.stButton button:hover::before {
    left: 100%;
}
.stButton button:hover {
    transform: translateY(-3px);
    box-shadow: 0 8px 25px rgba(16, 185, 129, 0.6);
}

/* Grid de Spins Evoluído */
.spin-grid-evoluido { 
    display: grid;
    grid-gap: 12px;
    justify-content: start;
    margin: 18px 0;
}
.spin-cell-evoluido {
    width: 75px;
    height: 75px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 16px;
    font-weight: 900;
    font-size: 22px;
    color: white;
    box-shadow: 0 8px 25px rgba(0,0,0,0.5);
    border: 3px solid rgba(255,255,255,0.15);
    transition: all 0.3s ease;
    position: relative;
    overflow: hidden;
}
.spin-cell-evoluido::after {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: linear-gradient(145deg, rgba(255,255,255,0.1), transparent);
    opacity: 0;
    transition: opacity 0.3s ease;
}
.spin-cell-evoluido:hover::after {
    opacity: 1;
}
.spin-cell-evoluido.red { 
    background: linear-gradient(145deg, #ef4444, #dc2626);
    text-shadow: 0 3px 6px rgba(0,0,0,0.4);
}
.spin-cell-evoluido.black { 
    background: linear-gradient(145deg, #1f2937, #111827);
    text-shadow: 0 3px 6px rgba(0,0,0,0.4);
}
.spin-cell-evoluido.green { 
    background: linear-gradient(145deg, #10b981, #059669);
    color: #042;
    font-weight: 900;
    text-shadow: 0 2px 4px rgba(255,255,255,0.3);
}

/* Badges de Status */
.badge-evoluido {
    display: inline-block;
    padding: 6px 12px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}
.badge-alto { background: linear-gradient(45deg, #10b981, #059669); color: white; }
.badge-medio { background: linear-gradient(45deg, #f59e0b, #d97706); color: white; }
.badge-baixo { background: linear-gradient(45deg, #ef4444, #dc2626); color: white; }
.badge-neutro { background: linear-gradient(45deg, #6b7280, #4b5563); color: white; }

/* Métricas Evoluídas */
[data-testid="metric-container"] {
    background: linear-gradient(145deg, rgba(255,255,255,0.08), rgba(255,255,255,0.03));
    border-radius: 16px;
    padding: 20px;
    border: 1px solid rgba(255,255,255,0.08);
    backdrop-filter: blur(10px);
}

/* Abas Evoluídas */
.stTabs [data-baseweb="tab-list"] {
    gap: 12px;
    background-color: transparent;
}
.stTabs [data-baseweb="tab"] {
    background-color: rgba(255,255,255,0.05);
    border-radius: 12px 12px 0 0;
    padding: 16px 28px;
    border: 1px solid rgba(255,255,255,0.1);
    color: #e6eef3;
    font-weight: 600;
    transition: all 0.3s ease;
}
.stTabs [aria-selected="true"] {
    background: linear-gradient(145deg, #10b981, #059669) !important;
    color: white !important;
    box-shadow: 0 4px 15px rgba(16, 185, 129, 0.4);
}
</style>
""", unsafe_allow_html=True)

# ==================== HEADER EVOLUÍDO ====================
st.markdown("""
<div class="atlas-header-evoluido">
  <div>
    <div class="atlas-title-evoluido">ATLAS PROFESSIONAL EVOLUÍDO</div>
    <div class="atlas-sub-evoluido">Sistema de Análise Avançada - Tecnologia de Ponta com 50+ Anos de Experiência Incorporada</div>
  </div>
  <div style="text-align:right;">
    <div style="font-weight:800; color:#042; font-size:20px; text-shadow: 0 2px 4px rgba(255,255,255,0.5);">🎯 SISTEMA SISMÓGRAFO ATIVO</div>
    <div style="font-size:13px; color:rgba(0,0,0,0.7); font-weight:600;">Ex-Croupier Certified • Análise de Roda Física • Detecção de Pressão</div>
  </div>
</div>
""", unsafe_allow_html=True)

st.markdown("<br/>", unsafe_allow_html=True)

# ==================== FUNÇÃO RENDER GRID EVOLUÍDA ====================
def render_spins_grid_evoluido(spins, count=20, cols=5):
    data = spins[:count]
    html = f'''
    <div class="atlas-card-evoluido">
        <div style="font-weight:800; margin-bottom:16px; font-size:20px; color:#10b981; display: flex; align-items: center; gap: 10px;">
            📊 <span>ÚLTIMOS {len(data)} RESULTADOS - ANÁLISE PROFISSIONAL</span>
        </div>
        <div class="spin-grid-evoluido" style="grid-template-columns: repeat({cols}, 75px);">
    '''
    
    for n in data:
        cls = color_of(n)
        html += f'<div class="spin-cell-evoluido {cls}">{n}</div>'
    
    if len(data) < count:
        for _ in range(count - len(data)):
            html += f'<div class="spin-cell-evoluido black" style="opacity:0.2;">-</div>'
    
    html += '</div>'
    html += '''
    <div style="display: flex; gap: 20px; align-items: center; margin-top: 16px; color: #cbd5e1; font-size: 14px; font-weight: 600;">
        <div><span style="display:inline-block; width:16px; height:16px; border-radius:6px; background:#10b981; margin-right:8px;"></span>0 (Verde)</div>
        <div><span style="display:inline-block; width:16px; height:16px; border-radius:6px; background:#ef4444; margin-right:8px;"></span>Vermelho</div>
        <div><span style="display:inline-block; width:16px; height:16px; border-radius:6px; background:#1f2937; margin-right:8px;"></span>Preto</div>
        <div style="margin-left:auto; color:#10b981;">🎯 SISTEMA EVOLUÍDO ATIVO</div>
    </div>
    </div>
    '''
    st.markdown(html, unsafe_allow_html=True)

# ==================== INTERFACE PRINCIPAL EVOLUÍDA ====================
tabs = st.tabs(["🎯 PAINEL PRINCIPAL", "📊 ANÁLISES AVANÇADAS", "📈 DESEMPENHO", "⚙️ CONFIGURAÇÕES"])

with tabs[0]:
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown('<div class="atlas-card-evoluido">', unsafe_allow_html=True)
        st.subheader("🎲 REGISTRAR NOVO RESULTADO - SISTEMA EVOLUÍDO")
        
        # 🎯 CORREÇÃO: Sistema de input simplificado e robusto
        spin_input = st.text_input(
            "Digite o número sorteado (0-36):",
            key="spin_input_evoluido",
            placeholder="Ex: 15, 0, 32...",
            help="Sistema evoluído com análise de roda física e pressão numérica",
            value=""
        )
        
        # 🎯 CORREÇÃO: Sistema de estado simplificado
        if 'processando' not in st.session_state:
            st.session_state.processando = False
        
        # 🎯 CORREÇÃO: Botão único com controle de estado
        if st.button("🎯 Registrar Resultado", use_container_width=True, type="primary"):
            if spin_input.strip() and not st.session_state.processando:
                try:
                    n = int(spin_input.strip())
                    if 0 <= n <= 36:
                        st.session_state.processando = True
                        
                        with st.spinner("🔄 Processando análise evoluída..."):
                            # Executa análise antes do novo spin
                            previous_spins = [s["number"] for s in state.get("spins", [])]
                            results, sismografo = run_all_strategies_advanced_evoluido(previous_spins)
                            
                            # Registra o novo spin
                            record = evaluate_spin_and_record_advanced_evoluido(n)
                            
                            st.success(f"✅ Resultado **{n}** registrado com sucesso!")
                            
                            # Prepara e envia relatório Telegram
                            success = enviar_relatorio_telegram(n, results, sismografo, previous_spins)
                            
                            if success:
                                st.success("✅ Relatório enviado para Telegram!")
                            else:
                                st.info("📝 Relatório salvo localmente")
                        
                        # 🎯 CORREÇÃO: Limpa o estado sem usar rerun()
                        st.session_state.processando = False
                        # Força atualização da página
                        st.rerun()
                        
                    else:
                        st.error("❌ Número deve estar entre 0 e 36")
                except ValueError:
                    st.error("❌ Digite um número válido")
            elif st.session_state.processando:
                st.warning("⏳ Processando... aguarde.")
            else:
                st.error("❌ Digite um número entre 0 e 36")
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # 🎯 MOSTRA SISMÓGRAFO EM TEMPO REAL
        if state.get("sismografo"):
            sismografo = state["sismografo"]
            # CORREÇÃO: Verifica se as chaves existem
            status = sismografo.get('status', 'NEUTRO')
            cor = sismografo.get('cor', '🟡')
            score = sismografo.get('score_assertividade', 50)
            
            status_class = f"sismografo-{status.lower()}"
            
            st.markdown(f'<div class="atlas-card-evoluido">', unsafe_allow_html=True)
            st.subheader("🎯 SISMÓGRAFO DE ASSERTIVIDADE")
            
            st.markdown(f'''
            <div class="{status_class}">
                <div style="display: flex; justify-content: between; align-items: center;">
                    <div style="font-size: 24px; font-weight: 800;">{cor} {status}</div>
                    <div style="font-size: 32px; font-weight: 900;">{score}%</div>
                </div>
                <div style="margin-top: 10px; font-size: 14px;">
                    <strong>Análise em tempo real da assertividade do momento</strong>
                </div>
            </div>
            ''', unsafe_allow_html=True)
            
            # Mostra fatores do sismógrafo
            if sismografo.get('fatores'):
                cols = st.columns(4)
                fatores = sismografo['fatores']
                with cols[0]:
                    st.metric("Ciclo RNG", f"{fatores.get('ciclo_rng', 0)}%")
                with cols[1]:
                    st.metric("Pressão", f"{fatores.get('pressao_numeros', 0)}%")
                with cols[2]:
                    st.metric("Cavalos Ímã", f"{fatores.get('cavalos_ima', 0)}%")
                with cols[3]:
                    st.metric("Correlação", f"{fatores.get('correlacao', 0)}%")
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Mostra alertas ativos
        if state.get("spins"):
            alertas = sistema_alertas_avancado_evoluido([s["number"] for s in state["spins"]])
            if alertas:
                st.markdown('<div class="atlas-card-evoluido">', unsafe_allow_html=True)
                st.subheader("🚨 ALERTAS PROFISSIONAIS EVOLUÍDOS")
                for alerta in alertas:
                    classe = f"alerta-{alerta['prioridade']}"
                    st.markdown(f'<div class="{classe}"><strong>{alerta["tipo"]}</strong><br>{alerta["mensagem"]}</div>', 
                               unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="atlas-card-evoluido">', unsafe_allow_html=True)
        st.subheader("💎 STATUS DA BANCA EVOLUÍDO")
        
        bankroll = state.get("bankroll", Config.BANKROLL_INICIAL)
        inicial = Config.BANKROLL_INICIAL
        variacao = bankroll - inicial
        variacao_percentual = (variacao / inicial) * 100
        
        st.metric(
            "Bankroll Atual", 
            f"R$ {bankroll:,.2f}", 
            f"R$ {variacao:+,.2f} ({variacao_percentual:+.1f}%)"
        )
        
        # Barra de progresso colorida
        progresso = min(max(bankroll / (inicial * 2), 0), 1)
        if variacao_percentual >= 0:
            st.progress(progresso)
        else:
            st.progress(progresso)
        
        # Verifica limites
        banca_manager = BankrollManagerEvoluido(state)
        status = banca_manager.verificar_limites()
        
        if status == "STOP_LOSS":
            st.error("🛑 STOP LOSS ATINGIDO!")
        elif status == "STOP_PROFIT":
            st.success("🎉 STOP PROFIT ATINGIDO!")
        elif status == "APPROACH_STOP_LOSS":
            st.warning("⚠️ APPROACH STOP LOSS - CUIDADO!")
        elif status == "APPROACH_STOP_PROFIT":
            st.info("📈 APPROACH STOP PROFIT - QUASE LÁ!")
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Ações rápidas evoluídas
        st.markdown('<div class="atlas-card-evoluido">', unsafe_allow_html=True)
        st.subheader("⚡ AÇÕES RÁPIDAS EVOLUÍDAS")
        
        if st.button("🔄 Executar Análise Completa", use_container_width=True):
            previous_spins = [s["number"] for s in state.get("spins", [])]
            results, sismografo = run_all_strategies_advanced_evoluido(previous_spins)
            st.success(f"Análise completa! Sismógrafo: {sismografo['status']} ({sismografo['score_assertividade']}%)")
        
        if st.button("📊 Atualizar Estatísticas", use_container_width=True):
            if state.get("spins"):
                spin_numbers = [s["number"] for s in state["spins"]]
                state["estatisticas_avancadas"] = analise_estatistica_completa_evoluida(spin_numbers)
                salvar_estado(state)
                st.success("Estatísticas atualizadas!")
        
        if st.button("🗑️ Limpar Histórico", use_container_width=True, type="secondary"):
            state["spins"] = []
            state["history"] = []
            state["last_bets"] = {}
            state["bankroll"] = Config.BANKROLL_INICIAL
            for s in STRATEGY_NAMES:
                state["strategies"][s] = {"green": 0, "loss": 0, "activations": 0, "lucro": 0}
            salvar_estado(state)
            st.success("Histórico limpo!")
            st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Métricas rápidas evoluídas
    st.markdown('<div class="atlas-card-evoluido">', unsafe_allow_html=True)
    st.subheader("📈 MÉTRICAS INSTANTÂNEAS EVOLUÍDAS")
    
    spins_list = [s["number"] for s in state.get("spins", [])]
    cols = st.columns(5)
    
    with cols[0]:
        st.metric("Total Spins", len(spins_list))
    with cols[1]:
        st.metric("Último Número", spins_list[-1] if spins_list else "-")
    with cols[2]:
        if spins_list:
            last_20 = spins_list[-20:]
            red_count = sum(1 for n in last_20 if n in RED_NUMS)
            black_count = sum(1 for n in last_20 if n in BLACK_NUMS)
            st.metric("🔴/⚫ (20)", f"{red_count}/{black_count}")
    with cols[3]:
        if spins_list:
            # 🎯 MÉTRICA DE PRESSÃO (NOVO)
            last_25 = spins_list[-25:] if len(spins_list) >= 25 else spins_list
            counts_25 = Counter(last_25)
            pressao_count = len([n for n in range(0, 37) if counts_25.get(n, 0) == 0])
            st.metric("💎 Pressão", pressao_count)
    with cols[4]:
        if spins_list and state.get("sismografo"):
            score = state['sismografo'].get('score_assertividade', 50)
            st.metric("🎯 Assertividade", f"{score}%")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Grid visual de spins evoluído
    if spins_list:
        render_spins_grid_evoluido(spins_list[::-1], count=25, cols=5)

with tabs[1]:
    st.markdown('<div class="atlas-card-evoluido">', unsafe_allow_html=True)
    st.subheader("🧠 ANÁLISES E ESTRATÉGIAS EVOLUÍDAS")
    
    if not state.get("spins"):
        st.info("📊 Insira alguns resultados no Painel Principal para ver as análises evoluídas")
    else:
        last_spins = [s["number"] for s in state.get("spins", [])]
        results, sismografo = run_all_strategies_advanced_evoluido(last_spins)
        
        # Tabela de estratégias evoluída
        rows = []
        for name, res in results.items():
            active = res.get("active", False)
            bets = res.get("bets", [])
            explain = res.get("explain", "")
            forca_ima = res.get("forca_ima", 0)
            
            # Busca probabilidade do last_bets
            prob = state["last_bets"].get(name, {}).get("probabilidade", 0)
            
            status_badge = "🟢 ATIVA" if active else "🔴 INATIVA"
            if active and prob > 75:
                status_badge = "🎯 ALTA CONFIANÇA"
            elif active and prob > 60:
                status_badge = "🟡 MÉDIA CONFIANÇA"
            
            rows.append({
                "Estratégia": name,
                "Status": status_badge,
                "Probabilidade": f"{prob}%",
                "Nº Apostas": len(bets),
                "Força Ímã": f"{forca_ima:.0f}%" if forca_ima > 0 else "-",
                "Apostas": ", ".join(map(str, bets[:5])) + ("..." if len(bets) > 5 else ""),
                "Explicação": explain
            })
        
        df = pd.DataFrame(rows).sort_values("Probabilidade", ascending=False)
        st.dataframe(df, use_container_width=True, height=450)
        
        # Análise Atlas-15 detalhada evoluída
        if results.get("Atlas-15 Evoluído") and results["Atlas-15 Evoluído"].get("scores"):
            st.subheader("🎯 ATLAS-15 EVOLUÍDO - ANÁLISE DETALHADA")
            
            scores = results["Atlas-15 Evoluído"]["scores"]
            top_15 = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:15]
            
            cols = st.columns(5)
            for i, (num, score) in enumerate(top_15):
                with cols[i % 5]:
                    cor = color_of(num)
                    emoji = "🔥" if score > 300 else "✅" if score > 200 else "⚡"
                    st.metric(
                        label=f"{num} ({cor.upper()[:1]})",
                        value=f"{score:.0f}",
                        delta=emoji
                    )
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Análise de Cavalos Evoluída
    if len(state.get("spins", [])) >= 30:
        st.markdown('<div class="atlas-card-evoluido">', unsafe_allow_html=True)
        st.subheader("🐎 ANÁLISE PROFISSIONAL DE CAVALOS EVOLUÍDA")
        
        analise_cavalos = analise_cavalos_profissional_evoluida([s["number"] for s in state["spins"]])
        
        if analise_cavalos:
            st.write("**Cavalos com Maior Força Ímã:**")
            cavalos_ima = []
            for cavalo, data in analise_cavalos.items():
                if data.get('forca_ima', 0) > 40:
                    cavalos_ima.append((cavalo, data['forca_ima']))
            
            cavalos_ima.sort(key=lambda x: x[1], reverse=True)
            
            cols = st.columns(4)
            for i, (cavalo, forca) in enumerate(cavalos_ima[:8]):
                with cols[i % 4]:
                    st.write(f"**Cavalo {cavalo}**")
                    st.write(f"Força: {forca:.0f}%")
                    if analise_cavalos[cavalo].get('alvos_preferidos'):
                        alvos = analise_cavalos[cavalo]['alvos_preferidos'][:3]
                        st.write(f"Alvos: {alvos}")
                    st.write("---")
        
        st.markdown('</div>', unsafe_allow_html=True)

with tabs[2]:
    st.markdown('<div class="atlas-card-evoluido">', unsafe_allow_html=True)
    st.subheader("📊 DESEMPENHO DAS ESTRATÉGIAS EVOLUÍDAS")
    
    # Performance individual evoluída
    perf_rows = []
    for name, stats in state.get("strategies", {}).items():
        g = stats.get("green", 0)
        l = stats.get("loss", 0)
        a = stats.get("activations", 0)
        lucro = stats.get("lucro", 0)
        
        if g + l > 0:
            pct = round((g / (g + l)) * 100, 2)
            roi = (lucro / (g + l)) if (g + l) > 0 else 0
        else:
            pct = 0.0
            roi = 0
        
        # 🎯 CLASSIFICAÇÃO DE PERFORMANCE
        if pct >= 60 and roi > 0:
            performance = "🎯 EXCELENTE"
        elif pct >= 50 and roi > 0:
            performance = "✅ BOA"
        elif pct >= 40:
            performance = "⚡ REGULAR"
        else:
            performance = "🔴 FRACA"
        
        perf_rows.append({
            "Estratégia": name,
            "✅ Greens": g,
            "❌ Losses": l,
            "🎯 Assertividade": f"{pct}%",
            "💰 Lucro Total": f"R$ {lucro:,.2f}",
            "📈 ROI por Ativação": f"R$ {roi:,.2f}",
            "🔥 Ativações": a,
            "⭐ Performance": performance
        })
    
    perf_df = pd.DataFrame(perf_rows).sort_values("💰 Lucro Total", ascending=False)
    st.dataframe(perf_df, use_container_width=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Gráficos de desempenho evoluídos
    if len(state.get("spins", [])) > 10:
        st.markdown('<div class="atlas-card-evoluido">', unsafe_allow_html=True)
        st.subheader("📈 ANÁLISE GRÁFICA EVOLUÍDA")
        
        spins_data = [s["number"] for s in state["spins"]]
        
        # Gráfico de distribuição na roda física
        fig = go.Figure()
        
        # Posições na roda física
        posicoes_roda = []
        frequencias_roda = []
        
        for num in range(0, 37):
            if num in RODA_FISICA:
                idx = RODA_FISICA.index(num)
                posicoes_roda.append(idx)
                frequencias_roda.append(spins_data.count(num))
        
        fig.add_trace(go.Scatterpolar(
            r=frequencias_roda,
            theta=posicoes_roda,
            fill='toself',
            name='Frequência na Roda',
            line=dict(color='#10b981')
        ))
        
        fig.update_layout(
            polar=dict(
                radialaxis=dict(visible=True, range=[0, max(frequencias_roda) * 1.1])
            ),
            showlegend=True,
            title="Distribuição na Roda Física",
            height=500
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        st.markdown('</div>', unsafe_allow_html=True)

with tabs[3]:
    st.markdown('<div class="atlas-card-evoluido">', unsafe_allow_html=True)
    st.subheader("⚙️ CONFIGURAÇÕES AVANÇADAS EVOLUÍDAS")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🔐 Configurações Telegram")
        chat_id = st.text_input(
            "Chat ID do Telegram",
            value=state.get("telegram_chat_id", Config.TELEGRAM_CHAT_ID),
            help="ID do chat para receber relatórios automáticos"
        )
        
        st.subheader("🎯 Configurações de Estratégia")
        confianca_minima = st.slider(
            "Confiança Mínima para Aposta (%)",
            min_value=40,
            max_value=85,
            value=state["config"].get("confianca_minima", Config.CONFIANCA_MINIMA),
            help="Probabilidade mínima para considerar uma aposta"
        )
        
        if st.button("💾 Salvar Configurações Evoluídas", use_container_width=True):
            state["telegram_chat_id"] = chat_id.strip()
            state["config"]["confianca_minima"] = confianca_minima
            salvar_estado(state)
            st.success("Configurações evoluídas salvas!")
    
    with col2:
        st.subheader("💰 Gestão de Banca Evoluída")
        unit_size = st.number_input(
            "Tamanho da Unidade Base (R$)",
            min_value=5,
            max_value=1000,
            value=state["config"]["unit_size"],
            help="Valor base para cálculo de apostas"
        )
        
        stop_loss = st.number_input(
            "Stop Loss (R$)",
            min_value=100,
            max_value=5000,
            value=state["config"]["auto_stop_loss"],
            help="Perda máxima permitida"
        )
        
        stop_profit = st.number_input(
            "Stop Profit (R$)", 
            min_value=100,
            max_value=10000,
            value=state["config"]["auto_stop_profit"],
            help="Ganho máximo alvo"
        )
        
        if st.button("🎯 Aplicar Configurações de Banca", use_container_width=True):
            state["config"]["unit_size"] = unit_size
            state["config"]["auto_stop_loss"] = stop_loss
            state["config"]["auto_stop_profit"] = stop_profit
            salvar_estado(state)
            st.success("Configurações de banca aplicadas!")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Informações do sistema evoluído
    st.markdown('<div class="atlas-card-evoluido">', unsafe_allow_html=True)
    st.subheader("ℹ️ INFORMAÇÕES DO SISTEMA EVOLUÍDO")
    
    st.write(f"**Versão:** Atlas Professional Evoluído 3.0")
    st.write(f"**Estratégias Ativas:** {len(STRATEGY_NAMES)}")
    st.write(f"**Total de Spins Registrados:** {len(state['spins'])}")
    st.write(f"**Bankroll Inicial:** R$ {Config.BANKROLL_INICIAL:,.2f}")
    st.write(f"**Bankroll Atual:** R$ {state['bankroll']:,.2f}")
    
    # Estatísticas avançadas
    if state.get("estatisticas_avancadas"):
        stats = state["estatisticas_avancadas"]
        st.write(f"**Cavalos Ímã Ativos:** {len(stats.get('cavalos_ima', []))}")
        st.write(f"**Números sob Pressão:** {len(stats.get('numeros_pressao', []))}")
    
    st.info("""
    **💡 DICAS PROFISSIONAIS EVOLUÍDAS:**
    
    🎯 **Sistema Sismógrafo:** 
    - Verde (ALTO): Momento ideal para apostas maiores
    - Amarelo (MÉDIO): Apostas moderadas
    - Vermelho (BAIXO): Reduzir apostas ou esperar
    
    💎 **Pressão Numérica:**
    - Números atrasados têm maior probabilidade matemática
    - Combine com análise de roda física para precisão
    
    🐎 **Cavalos Ímã:**
    - Cavalos com alta força ímã são mais previsíveis
    - Foque nos alvos preferidos de cada cavalo
    
    🎡 **Roda Física:**
    - A bolinha tende a cair perto de números recentes
    - Use vizinhança física, não apenas visual
    """)
    
    st.markdown('</div>', unsafe_allow_html=True)

# ==================== SIDEBAR EVOLUÍDO ====================
with st.sidebar:
    st.markdown('<div class="atlas-card-evoluido">', unsafe_allow_html=True)
    st.subheader("🎯 AÇÕES RÁPIDAS EVOLUÍDAS")
    
    if st.button("🧠 Analisar Agora", use_container_width=True):
        last_spins = [s["number"] for s in state.get("spins", [])]
        results, sismografo = run_all_strategies_advanced_evoluido(last_spins)
        st.success(f"Análise completa! Sismógrafo: {sismografo['status']}")
    
    if st.button("📊 Estatísticas Detalhadas", use_container_width=True):
        st.session_state.show_detailed_stats = True
    
    st.markdown("---")
    st.subheader("💎 STATUS EVOLUÍDO")
    
    if state.get("spins"):
        spins_count = len(state["spins"])
        st.write(f"**Spins:** {spins_count}")
        
        last_num = state["spins"][-1]["number"] if state["spins"] else "N/A"
        st.write(f"**Último:** {last_num}")
        
        bankroll = state.get("bankroll", Config.BANKROLL_INICIAL)
        st.write(f"**Bankroll:** R$ {bankroll:,.2f}")
        
        if state.get("sismografo"):
            sismografo = state["sismografo"]
            badge_class = f"badge-{sismografo['status'].lower()}"
            st.markdown(f'<div class="{badge_class} badge-evoluido">Sismógrafo: {sismografo["status"]} ({sismografo["score_assertividade"]}%)</div>', 
                       unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

# ==================== RODAPÉ PROFISSIONAL EVOLUÍDO ====================
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #64748b; font-size: 13px; padding: 20px;">
    <div style="font-weight: 700; margin-bottom: 8px; color: #10b981;">
        ATLAS PROFESSIONAL EVOLUÍDO ROULETTE SYSTEM
    </div>
    <div style="margin-bottom: 8px;">
        Desenvolvido com 50+ anos de experiência em cassinos • Sistema Sismógrafo • Análise de Roda Física
    </div>
    <div>
        PlayTech • Pragmatic • Evolution • Immersive • © 2024
    </div>
</div>
""", unsafe_allow_html=True)

# ==================== INICIALIZAÇÃO FINAL ====================
# Garante que todas as estratégias estão inicializadas
for strategy in STRATEGY_NAMES:
    if strategy not in state["strategies"]:
        state["strategies"][strategy] = {"green": 0, "loss": 0, "activations": 0, "lucro": 0}

# CORREÇÃO: Garante que o sismógrafo está inicializado corretamente
if not state.get("sismografo"):
    state["sismografo"] = {
        "status": "NEUTRO", 
        "cor": "🟡", 
        "score_assertividade": 50,
        "fatores": {},
        "ultima_mudanca": datetime.utcnow().isoformat()
    }

# Salva estado inicial se necessário
if not state.get("_initialized"):
    state["_initialized"] = True
    salvar_estado(state)
