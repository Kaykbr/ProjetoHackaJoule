# Pitch: Doa Certo

## Estrutura dos slides (máx. 10)

1. **Gancho:** uma foto de pilhas de roupa doada estragando ao lado de um ponto onde faltam cobertores.
   "Não falta vontade de doar. Falta saber o quê e onde."
2. **Problema:** doações descoordenadas: excesso de um item, falta de outro, desperdício. ONGs pedem por
   WhatsApp e Instagram, em texto solto, sem visão agregada. *(Use o número atualizado da população em
   situação de rua no CadÚnico, que passa de 300 mil pessoas no Brasil. Confira a fonte mais recente
   antes de apresentar: Observatório POLOS/UFMG ou MDHC.)*
3. **Solução:** um painel único de demandas reais, priorizadas e mapeadas.
4. **Demo** (ao vivo, ver roteiro abaixo).
5. **Como a IA é usada:** a tabela "Usa IA?" do README. Mensagem: *IA só onde texto vira dado.*
   Prova: em 37 mensagens com armadilhas (incluindo espanhol e tentativas de prompt injection), as
   regras locais acertam 19 e o Gemini acerta 37, a ~US$ 0,0001 por mensagem. Com regras primeiro,
   a mesma acurácia sai com 19% menos chamadas de IA. E nenhum item sem evidência no texto chega à
   tela. Demo ao vivo: cole "20 marmitas e 10 cobertores" (selo "lido sem IA") e repita a
   mensagem (selo "já lido antes").
6. **Ética e privacidade:** só pontos de atendimento, nunca pessoas · PII removida antes do LLM ·
   ONG sempre confirma · funciona sem IA.
7. **Custo:** print do Medidor de IA (custo por chamada em frações de centavo; 0 no plano gratuito).
8. **Impacto e sustentabilidade:** menos doação desperdiçada = menos resíduo têxtil e alimentar;
   métricas: itens entregues, % de demandas atendidas.
9. **Próximos passos:** WhatsApp, validação de ONG por CNPJ, notificação por região, parceria com
   prefeitura (Consultório na Rua / CRAS).
10. **Fechamento:** "A doação certa, no lugar certo, na hora certa."

## Roteiro da demo (3 minutos)

1. **Mapa (20s):** "Cada círculo é um ponto de atendimento de uma ONG, com o número de pedidos. A cor
   é a urgência, calculada por regras que qualquer pessoa entende." Clique num círculo: a lista
   destaca o ponto. Passe o mouse no selo de urgência para mostrar o *Por que essa prioridade*.
2. **Painel da ONG (60s):** *Sou ONG*, clique em *Usar mensagem de exemplo* (ou em *Ditar*) e depois em
   *Organizar com IA*. Mostre os cards por item, a quantidade estimada em amarelo e o selo
   **"1 dado pessoal removido antes do envio"**. Ajuste a urgência e publique. "A IA sugere, a ONG
   decide."
3. **Frente fria (30s):** volte ao mapa, abra o menu **⋯** da faixa de clima e escolha *Simular frente
   fria (6°C)*. As críticas sobem de 2 para 6 e os cobertores vão para o topo, com a razão escrita.
   "Isso não é IA, é regra mais dado aberto de clima, com custo zero."
4. **Doador (50s):** *Quero doar*, clique no primeiro exemplo, *Continuar*, confira os itens e clique em
   *Ver onde doar*. Mostre a recomendação ("Leve para…") com os motivos e a linha no mini-mapa, clique
   em *Doar 3 aqui* e depois em *Concluir*.
5. **Impacto e transparência (20s):** em *Impacto*, a cobertura por categoria e o bloco "Onde entra a
   IA". Clique em *Como medimos o uso de IA* (ou *Transparência* no rodapé): o medidor de cada
   mensagem lida e a avaliação 37/37 do Gemini contra 19/37 das regras.

Se o júri abrir no celular: a navegação fica embaixo e a lista do mapa sobe arrastando a alça.

### Roteiro da central de operações (2 minutos, depois da demo acima)

Abra *Sou ONG → Central de operações* (ou `/operacao`).
1. **Voz (40s):** toque no microfone e fale um relato, ou clique em *Chuva no Anhangabaú*. O ponto
   aparece pulsando no mapa e o cartão mostra o que a IA extraiu, inclusive "dado pessoal removido".
   Se o local não for reconhecido, selecione o ponto e **arraste o marcador** até o lugar certo.
2. **Radar (40s):** clique em *Frente fria brusca*. O mapa passa para *Previsão +24h*, os pontos
   críticos pulsam e o alerta mostra "+115% em agasalhos". "Isso é fórmula com dado aberto de
   clima, não chute de IA."
3. **Rota (40s):** clique em *Gerar rota inteligente*. A linha ciano percorre as ruas, e o painel
   mostra o roteiro do motorista, os km, o tempo, o % atendido e o CO2 evitado. Toque em
   **WhatsApp** ou **Maps**: "a rota vai para o celular do motorista". Clique em *Concluir
   entregas* e mostre os KPIs do topo subindo.
4. **Outra cidade (20s):** troque o seletor para *Fortaleza*. "Aqui não existe frente fria: o radar
   oferece calor extremo e chuva forte, e o calor pede água." Clique em *Calor extremo*.

**Antes de subir no palco:** no site público, rode `scripts\servir.ps1 -ResetDados` (ou abra a
central com `?admin=<token de scripts/.admin-token>` e clique em *Reiniciar demo* em cada cidade).
Deixe a simulação de clima desligada. Localmente: `python -m app.seed` ou `./start_demo.sh --reset`.

**Link para o júri:** https://doacerto.tailc7bf84.ts.net (do próprio PC, via Tailscale Funnel; ver
README). Confira que o PC não vai desligar nem suspender.

## Perguntas prováveis do júri

- *"E se a ONG mentir ou for golpe?"* No MVP há o selo "verificada". O próximo passo é validar por
  CNPJ e exigir confirmação de entrega.
- *"Por que não deixar a IA decidir tudo?"* Porque decisões que afetam pessoas vulneráveis precisam
  ser explicáveis e auditáveis, e regra custa zero.
- *"Morador de rua usa o app?"* Não, e isso é proposital. Quem informa é quem já atende (ONG,
  voluntário, agente de saúde). Não expomos ninguém.
- *"Isso funciona fora de São Paulo?"* Funciona em três cidades com clima diferente (SP, Rio e
  Fortaleza). Uma cidade nova é um registro com centro, lugares conhecidos e cenários de clima
  plausíveis.
- *"Isso já foi testado com ONG de verdade?"* Ainda não, e é o próximo passo: um piloto com 1 ou 2
  ONGs de uma cidade. O protótipo prova a técnica; a adoção é o risco real.
- *"Quanto custa rodar?"* Mostre o medidor de IA. Mapa (OSM), clima (Open-Meteo) e LLM (plano
  gratuito) não custam nada no MVP.
