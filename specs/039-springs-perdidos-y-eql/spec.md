# Spec 039: springs perdidos con el bot apagado + mínimos iguales (EQL)

## Parte A: springs perdidos (implementado)

Problema: el bot solo miraba la última vela cerrada; un spring confirmado mientras la PC estaba apagada
se perdía en silencio. Ahora `WyckoffAlerter._recent_events` revisa la última vela y las 3 anteriores
(hasta 12 h), detectando cada evento con el DataFrame truncado en su vela (sin mirar el futuro). Los ya
avisados no se repiten (dedup por firma, persistida). Los tardíos salen marcados "ALERTA RETARDADA" con
el costo medido, y cuentan para "pares simultáneos".

Costo medido de entrar tarde (`delay_cost.py`, 860 IS + 525 OOS, mismo plan 72 h desde la entrada,
stop -10%, 0.1% comisión): 0 h +1.75/+1.68%; 4 h +1.31/+1.03; 8 h +0.99/+0.81; 12 h +0.90/+0.43;
24 h +0.44/+0.44 (IS/OOS). Costo unido por 4 h ~ -0.5 pp (IC95 [-0.96,-0.08]); a 24 h -1.29 pp, acierto
47-52%. Por eso el límite es 12 h: más viejo ya no se avisa.

## Parte B: EQL (mínimos iguales) como filtro del spring — criterio fijado ANTES de correr

Idea (contenido tipo ICT/SMC): un nivel tocado varias veces acumula más stops; su barrida debería ser
mejor que la de un mínimo simple. El nivel del bot es el mínimo de las últimas 20 velas; el spring EQL es
el mismo evento con la condición extra "al menos 2 velas del rango (sin contar la de ruptura) tienen su
mínimo dentro de la tolerancia del nivel". Es un subconjunto de los springs actuales.

Hipótesis (2, dirección fijada: EQL mejor): H1 tolerancia 0.3%; H2 tolerancia 0.6%.
Datos: springs del laboratorio (SpringH72_SL10, señal, 860 IS / 525 OOS), datos 4h de futuros.
Criterio (todo junto): diferencia de medias (EQL - resto) > 0 en IS y en OOS, y IC bootstrap por DÍA de la
muestra unida excluye 0 con nivel corregido por 2 comparaciones (IC 97.5%). Si no, no se aplica y no se
cambia el mensaje. Aunque apruebe, solo se registra/muestra como hipótesis hasta >= 50 alertas reales.

## Resultado parte B (resultado_eql.txt)

**Ninguna hipótesis aprueba, y el efecto va en la dirección OPUESTA a la esperada.**
- H1 (tolerancia 0.3%): 306 springs EQL vs 1,079 resto. IS -0.78 pp, OOS -3.07 pp, unido -1.64 pp,
  IC97.5% por día [-3.43, +0.09].
- H2 (tolerancia 0.6%): IS -0.31 pp, OOS -3.86 pp, unido -1.67 pp, IC [-3.82, +0.46].

Los springs cuyo mínimo fue tocado varias veces rinden menos (acierto 44-51% vs 58-65% en OOS). Lectura
posible, NO pre-registrada y por tanto solo exploratoria: un piso muy probado tiende a ser un soporte
real que se rompe de verdad, mientras que la barrida de un mínimo "limpio" atrapa más gente. No se actúa
sobre esto (los IC incluyen 0 y la dirección no estaba fijada de antemano); no se agrega EQL al bot.
