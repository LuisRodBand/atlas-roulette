import streamlit as st
import json
from datetime import datetime
from collections import Counter
import requests

# Configurações básicas
TELEGRAM_TOKEN = "7743493295:AAGRszg878ADYuWFbO7rAv_WGifv3xzWxfc"
TELEGRAM_CHAT_ID = "-1003031355230"
BANKROLL_INICIAL = 5000

# Inicializar estado
if 'spins' not in st.session_state:
    st.session_state.spins = []
if 'bankroll' not in st.session_state:
    st.session_state.bankroll = BANKROLL_INICIAL

# Dados da roleta
RED_NUMS = [1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36]
BLACK_NUMS = [2,4,6,8,10,11,13,15,17,20,22,24,26,28,29,31,33,35]

def cor_numero(numero):
    if numero == 0: return "🟢"
    return "🔴" if numero in RED_NUMS else "⚫"

# Estratégias simples
def estrategia_atrasados(spins):
    if len(spins) < 10: return []
    counts = Counter(spins)
    return [num for num, count in counts.most_common()[-6:]]

def estrategia_cores(spins):
    if len(spins) < 5: return []
    ultimas_cores = [cor_numero(n) for n in spins[-4:]]
    if len(set(ultimas_cores)) == 1:  # Mesma cor 4x seguidas
        return BLACK_NUMS[:8] if ultimas_cores[0] == "🔴" else RED_NUMS[:8]
    return []

# Interface
st.set_page_config(page_title="ATLAS ROULETTE", layout="centered")

st.markdown("""
<style>
    .main { background: #0f172a; color: white; }
    .stButton>button { 
        background: #10b981; 
        color: white; 
        border: none; 
        padding: 15px; 
        border-radius: 10px; 
        font-size: 18px; 
        width: 100%;
    }
    .card { 
        background: rgba(255,255,255,0.1); 
        padding: 15px; 
        border-radius: 10px; 
        margin: 10px 0; 
    }
</style>
""", unsafe_allow_html=True)

# Header
st.title("🎯 ATLAS ROULETTE")
st.write("Sistema Simplificado - iPhone")

# Painel principal
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("🎲 Registrar Resultado")
    numero = st.number_input("Número (0-36):", 0, 36, 0)
    
    if st.button("✅ Registrar"):
        st.session_state.spins.append(numero)
        
        # Calcular estratégias
        atrasados = estrategia_atrasados(st.session_state.spins)
        cores = estrategia_cores(st.session_state.spins)
        
        st.success(f"Número {numero} {cor_numero(numero)} registrado!")
        
        # Mostrar apostas recomendadas
        if atrasados:
            st.write("📊 **Atrasados**:", ", ".join(map(str, atrasados)))
        if cores:
            st.write("🎨 **Cores**:", ", ".join(map(str, cores)))

with col2:
    st.subheader("💰 Status")
    st.metric("Bankroll", f"R$ {st.session_state.bankroll}")
    st.metric("Total Spins", len(st.session_state.spins))

# Últimos resultados
if st.session_state.spins:
    st.subheader("📊 Últimos Números")
    ultimos = st.session_state.spins[-8:]
    cols = st.columns(8)
    for i, num in enumerate(ultimos):
        with cols[i]:
            st.write(f"{cor_numero(num)}")
            st.write(f"**{num}**")

# Botão limpar
if st.button("🗑️ Limpar Histórico"):
    st.session_state.spins = []
    st.session_state.bankroll = BANKROLL_INICIAL
    st.success("Histórico limpo!")
