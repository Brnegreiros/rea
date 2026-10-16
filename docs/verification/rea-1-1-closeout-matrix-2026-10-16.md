# REA-1.1 — Matriz de encerramento

Data: 16/10/2026, America/Manaus. Repositório: `Brnegreiros/rea`.
Branch: `fix/bcode-rea-1-1-containment`. Baseline lido: `5bc49548175ddba31a6593c62eed20d6339a00cb`.
Main local/remota: `6060de329de9f3636f63e24a2419847fd9d3f889`, intacta.

**Entrega desta rodada: matriz consolidada. A REA-1.1 continua PARCIAL; o parecer final ainda não foi emitido.**
O parecer operacional vigente permanece **NO-GO para produção, agentes irrestritos e integração**.
O protótipo fica congelado nesta sequência de encerramento. Não é necessário implementar mais capacidades para documentar uma negativa fundamentada.

## Critério de encerramento e critério de liberação

Concluir a auditoria significa dar disposição rastreável aos dez objetivos: evidência, limites, achados, severidade, correções propostas, testes e decisão. Não significa converter todos os controles em PASS. Um controle não demonstrado permanece NOT_TESTED e pode sustentar NO-GO. Se faltar investigação material, o relatório final deve declarar a auditoria limitada/encerrada com pendências; não poderá afirmar cobertura completa.

Liberar execução, merge ou integração exige decisão posterior. A autorização externa do protótipo não foi instalada no REA direto; a main também não contém as guardas preparadas na branch. Nenhuma dessas diferenças se resolve apenas mudando o texto do parecer.

## Os dez objetivos originais

PARCIAL é estado de cobertura do objetivo, não resultado de teste. PASS/FAIL/NOT_TESTED dos controles continuam nos registros de origem.

| # | Objetivo original | Cobertura | Evidência existente | Lacuna e disposição mínima |
| --- | --- | --- | --- | --- |
| O01 | Revisar os workflows de CI, release e publicação. | PARCIAL | E01: Guardas de identidade em release.yml, release-recovery.yml e website-pages.yml na branch; testes estruturais e nenhum diff em .github após o baseline 93064357. | Falta revisão de cobertura de todos os 29 workflows e ações locais: triggers, permissões, segredos, OIDC, refs e sinks. Main ainda não contém as guardas. **EC1**: Registrar cada workflow/ação local, efeitos, entradas não confiáveis, publicações e decisão; nenhuma execução de workflow necessária. |
| O02 | Inspecionar scripts de instalação, preparação e build. | PARCIAL | E01, E04, E07: npm ci com lifecycle desativado e builds isolados registrados; prepare e prepublishOnly estão declarados no package.json. | Build aprovado não equivale a revisão dos instaladores/setup/updaters/native hooks e de suas cadeias de download, escrita e elevação. **EC1**: Mapa dos entrypoints alcançáveis e seus efeitos; scripts desnecessários ficam explicitamente não executados/excluídos, sem instalação no host. |
| O03 | Auditar dependências e vulnerabilidades conhecidas. | NOT_TESTED | E01, E04, E07, E09: Lockfile e aquisição controlada preservados; isso identifica versões/integridade, mas não prova ausência de vulnerabilidades. | Não foi localizada evidência de SCA completa e atual do grafo aplicável. Há 722 entradas em packages, incluindo a raiz: 721 caminhos de dependência, não 721 pacotes únicos. **EC2**: Relatório datado com componente/versão/escopo, fonte/consulta, achados e limitações. Falha de consulta vira NOT_TESTED e bloqueio, nunca zero vulnerabilidades. |
| O04 | Validar licenças e integridade de componentes externos. | PARCIAL | E04, E09, E10: MIT principal, lock/hash, inventário npm e textos de licença já existentes; docs:check histórico incluiu consistência de metadados/licenças; cinco gitlinks fixados. | Falta revisão independente do fork para origem/revisão/avisos dos componentes efetivamente obtidos ou considerados. Inventário herdado declara lacunas clean-git-ref, minimisted e Frida; não foi revalidado cada arquivo upstream. **EC2**: Reconciliar inventário existente com lock/gitlinks/uso; registrar lacunas e separar bibliotecas empacotadas de motores externos/proprietários não habilitados, sem redistribuir engines. |
| O05 | Auditar as permissões das ferramentas MCP. | PARCIAL | E04, E05, E07: Seams CLI/MCP e um protocolo externo restrito foram testados; UID kernel separa operador e cliente do protótipo. | Falta mapa completo ferramenta→capacidade→efeito→autoridade→rota equivalente. 36 arquivos register*Tools.ts são localizadores, não contagem de ferramentas. Anotações/schema não são autorização. O protótipo não protege automaticamente o MCP/CLI direto. **EC1**: Cobertura de todas as ferramentas do catálogo/registradores e rotas sensíveis; execução, attach, modificação, export/update ficam negados fora do recorte já autorizado, sem criar gateway. |
| O06 | Investigar riscos de execução arbitrária, instrumentação e manipulação de processos. | PARCIAL | E02, E04, E05, E07: Frida source-read corrigido; herança base reduzida; preload explícito benigno e persistência literal comprovados em PTY; fixtures restritas usam autorização externa. | REA direto ainda aceita entradas explícitas sem a decisão externa do protótipo; instrumentação Frida/device/LLDB e provedores reais não homologados. **EC1**: Consolidar achados por entrada/processo e identificar caminhos fora do launcher; registrar capacidades não habilitadas e correções propostas, sem executar provedores ou ampliar o controlador. |
| O07 | Verificar controles de proteção de dados e credenciais. | PARCIAL | E01, E04, E05, E07, E11: Canários sintéticos, proteção de cabeçalhos/valores marcados, respostas privadas, TTL e posse de descarte ensaiados; nenhuma credencial real transferida. | Cobertura completa de sinks não demonstrada; valores explícitos/eco podem persistir na Evidence; DLP/dados reais e cópias externas não certificados. Exclusão no prazo falha sob EBUSY forçado. **EC1**: Mapa mínimo entrada→Evidence/log/export/backup conhecido→leitor→prazo→descarte; manter dados reais/export bruto excluídos e registrar falha de exclusão sem renovação de prazo. |
| O08 | Avaliar isolamento e limitação de recursos. | PARCIAL | E01, E07, E08, E11: VM descartável, UID/caps/no_new_privs, namespaces, rede negada, 512 MiB, 64 tarefas, 1 MiB de streams e encerramento foram observados em fixtures Linux. | Perda de ambos os guardiões, guardião vivo travado, armazenamento de controle totalmente indisponível, relógio e parte dos enforcers não ensaiados; browser suportado/OS/provedores seguem limitados. **EC3**: Transportar PASS estreitos e NOT_TESTED completos ao parecer. Esses riscos bloqueiam GO; para NO-GO não exigem novos testes nem implementação nesta sequência. |
| O09 | Executar testes determinísticos seguros em ambiente isolado. | PASS_NO_RECORTE | E01, E02, E04, E07, E08: Suítes históricas selecionadas e última rodada real com hashes, logs, falhas, métricas e descarte. A última rodada tem 48 PASS/8 NOT_TESTED em quatro suítes, não 56 aprovações de segurança. | Suíte integral, todos os sistemas/provedores, gate humano e critérios amplos restantes não executados; não somar rodadas sobrepostas como cobertura inédita. **EC3**: Reutilizar evidência rastreável; comparar hashes/ancestralidade e descrever limites. Repetir somente se futura alteração material invalidar um resultado, não por ser uma consolidação documental. |
| O10 | Emitir parecer de prontidão, com riscos residuais. | PENDENTE | E01, E04, E05, E07, E11: Decisões parciais consistentes: continuidade de avaliação sintética isolada; NO-GO para produção, agentes irrestritos e integração. | Ainda não há encerramento único dos dez objetivos com cobertura, riscos, prioridades e decisão. Esta matriz não se declara parecer final nem autoriza operação. **EC3**: Emitir parecer técnico final após classificar a cobertura restante. Pode ser NO-GO com pendências; não exigir que todos os testes passem para documentar a negativa. Aprovação humana de PR/merge é outra decisão. |

## Evidências existentes e validade

| ID | Registro | Escopo e limite |
| --- | --- | --- |
| E01 | [fork-runtime-validation-2026-10-15.md](fork-runtime-validation-2026-10-15.md) | Contenção/distribuição e browser: 206 PASS, 1 skip; build/typecheck e probe Linux limitados; não é auditoria dos 29 workflows. |
| E02 | [frida-source-read-2026-10-15.md](frida-source-read-2026-10-15.md) | Leitura Frida: 99 PASS; arquivo regular, 4 MiB, cancelamento/cleanup; não houve instrumentação nativa. |
| E03 | [provider-environment-2026-10-15.md](provider-environment-2026-10-15.md) | Herança base: 144 PASS, 1 skip históricos; produtor foi alterado depois e está coberto no registro E04; 2 oom_kill antigos sem atribuição. |
| E04 | [direct-environment-2026-10-15.md](direct-environment-2026-10-15.md) | Rotas diretas: 440 testes + 5 de documentação = 445 PASS, 8 skips; prova real de variável explícita/preload/evidência; SCA completa não executada. |
| E05 | [external-execution-authorization.md](../external-execution-authorization.md) | Contrato mínimo externo; definição de requisitos e retenção, sem integrar autorização ao runtime publicado. |
| E06 | [execution-authorization-acceptance-2026-10-15.json](execution-authorization-acceptance-2026-10-15.json) | Catálogo original de 28 critérios; estados da revisão de definição são históricos, não resultados atuais. |
| E07 | [controller-resource-storage-2026-10-16.md](controller-resource-storage-2026-10-16.md) | Última rodada: catálogo 20 PASS/0 FAIL/8 NOT_TESTED; JR 12 PASS; RR 4 PASS; RS/SF 12 PASS; 73 áreas vazias após expiração/recuperação e VM parada. |
| E08 | [controller-resource-storage-2026-10-16.json](controller-resource-storage-2026-10-16.json) | Logs, hashes, métricas, falhas de desenvolvimento, recuperação do operador e recibos de descarte da última rodada. |
| E09 | [THIRD_PARTY_NOTICES.md](../../THIRD_PARTY_NOTICES.md) | Avisos herdados: inventário npm/avisos runtime, componentes externos e lacunas de autoria documentadas; não é SCA nova nem homologação jurídica. |
| E10 | [README.md](../../licenses/README.md) | Proveniência/metodologia dos avisos e limites da verificação de licenças; inventário existente pode ser reaproveitado. |
| E11 | [controller-retention-2026-10-16.md](controller-retention-2026-10-16.md) | Posse de descarte, perda de um guardião, RR-04 EBUSY e recuperação tardia; CP-R02 e CP-R05 ainda qualificados. |
| E12 | [provider-process-environment.md](../provider-process-environment.md) | Contrato de compatibilidade/proveniência; allowlist da base não autoriza valores explícitos nem constitui sandbox. |

Os resultados são históricos para suas revisões. Nesta rodada nenhum teste de projeto foi executado, nenhuma VM iniciada e nenhuma SCA consultada. Não somar 206/99/144/445 entre rodadas: há sobreposição e diferentes revisões. A última rodada do protótipo tem quatro suítes distintas — 20/0/8 no catálogo, 12/0/0 JR, 4/0/0 RR e 12/0/0 RS/SF — sem certificar o produto inteiro.

Verificação local de correspondência dos arquivos gravados nos manifestos:

| Registro | Hashes iguais / registrados | Diferença e interpretação |
| --- | --- | --- |
| frida-source-read-2026-10-15 | 5/5 | Nenhuma diferença. |
| provider-environment-2026-10-15 | 15/16 | src/process/providerProcessEnvironment.ts O produtor alterado está no manifesto posterior E04, cujo hash atual corresponde. |
| direct-environment-2026-10-15 | 24/26 | docs/fork-execution-readiness.md; docs/provider-process-environment.md São dois documentos; os fontes/testes restantes correspondem. O link desta matriz acrescentado depois não é um reteste. |
| controller-resource-storage-2026-10-16 | 12/12 | Nenhuma diferença. |

Não houve mudanças em `.github` desde o baseline de contenção `930643577fa5f4c19d350a5c11eddad3e6c1ce0d`. Isso preserva a associação estrutural daqueles arquivos à evidência anterior; não homologa todos os workflows.

Inventário estático atual: 29 workflows; 722 entradas no objeto `packages` do lock, sendo uma raiz e 721 caminhos de dependência; 36 arquivos `register*Tools.ts`, que não equivalem a 36 ferramentas; cinco gitlinks externos. Os submódulos não estão inicializados nesta cópia: identidade Git foi observada, não uma inspeção nova de seu conteúdo.

Os avisos e inventários npm já existem. `licenses/README.md` descreve coleta upstream por arquivos com integridade e o alcance do check; isso não equivale a uma nova SCA ou garantia jurídica. `THIRD_PARTY_NOTICES.md` registra lacunas de avisos em clean-git-ref/minimisted/Frida e diferencia engines externas de material empacotado. Reutilizar esses registros evita reconstrução e downloads indiscriminados.

## Trabalho mínimo restante — escopo fechado

### EC1 — Fechar revisão estática e mapa de autoridade/dados

Objetivos: O01, O02, O05, O06, O07.

Entregável: Um registro por workflow/ação local, entrypoint de instalação/build e ferramenta/rota sensível; efeitos, entradas, autoridade, sinks e disposição. Reutilizar catálogos existentes.

Critério verificável: Nenhum item inventariado sem classificação; itens não inspecionáveis têm NOT_TESTED + impacto + bloqueio/escopo. Nenhuma ferramenta perigosa se torna habilitada.

Não exige nova implementação do protótipo, execução de alvos ou correção de código.
### EC2 — Fechar baseline de cadeia de suprimentos

Objetivos: O03, O04.

Entregável: Relatório de dependências/SCA datado com grafo npm do lock, opcionais/plataformas/site/dev e catálogo separado de engines/componentes externos; integridade/origem/licença, achados e limites por componente.

Critério verificável: Inventário/avisos existentes reconciliados; fontes/consultas e resultados preservados. Componentes sem grafo/consulta permanecem NOT_TESTED e não habilitados. Sem alegação de SCA completa quando houver exclusões.

Não exige nova implementação do protótipo, execução de alvos ou correção de código.

Se usar ferramenta de SCA, somente ambiente descartável com lifecycle desligado; consultas de metadados por API autorizada também são possíveis. Sem rodar instaladores/provedores.
### EC3 — Emitir parecer técnico final e registrar backlog

Objetivos: O08, O09, O10.

Entregável: Matriz de riscos por severidade/impacto/evidência, PASS/FAIL/NOT_TESTED por controle, cobertura dos dez objetivos, correções propostas, testes reais e decisão final por escopo.

Critério verificável: Parecer identificado por revisão/hash e evidências, com NO-GO onde houver bloqueios e critérios para reabertura. Não atestar revisão humana nem permissões de merge.

Não exige nova implementação do protótipo, execução de alvos ou correção de código.

**Ordem: EC1 → EC2 → EC3.** Este plano substitui, para o encerramento atual, próximos prompts históricos que sugeriam novas iterações do protótipo. As lacunas continuam registradas; ensaios futuros dependem de missão específica. Não há estimativa de dias ou percentual de conclusão: a gravidade/quantidade de achados da revisão restante não é conhecida. Uma constatação adicional vira risco e correção proposta; não dispara automaticamente outra implementação nesta sequência.

EC2 deve cobrir o grafo npm aplicável com data/fontes e manter inventário separado de motores, submódulos, material vendorizado e ferramentas proprietárias. Componente sem grafo ou consulta não recebe “sem vulnerabilidades”: fica NOT_TESTED, com impacto e exclusão/bloqueio registrados. Não instalar/rodar motores nativos para preencher uma coluna. A licença declarada é dado de inventário, não parecer jurídico.

EC3 deve conter matriz de riscos com severidade/impacto/arquivo/trecho e proposta mínima; relatório de dependências; resultado apenas dos testes efetivamente executados; PASS/FAIL/NOT_TESTED por controle; pendências e risco residual; decisão GO/NO-GO por escopo e critérios de reabertura. Evidência e limites de EC1/EC2 precisam acompanhar a conclusão. A declaração humana de prontidão de um eventual PR é separada; não é atestada por esta matriz.

## Bloqueios de GO que não exigem ampliar o protótipo para emitir NO-GO

| ID | Prioridade | Fato ou limite | Disposição no fechamento |
| --- | --- | --- | --- |
| G01 | ALTA | Guardas de distribuição existem apenas na branch; main preservada não as contém. A cobertura dos demais workflows está incompleta. | OBSERVED_SOURCE; EC1; manter bloqueio de GO. |
| G02 | ALTA_POR_INCERTEZA_OPERACIONAL | SCA completa/atual não demonstrada; nenhuma ausência de CVE deve ser inferida. | NOT_TESTED; EC2; manter bloqueio de GO. |
| G03 | MEDIA_ALTA_SE_REDISTRIBUIDO | Inventário/avisos existem, mas lacunas e termos de componentes externos precisam de disposição; MIT principal não cobre tudo. Não é conclusão jurídica. | DECLARED_UPSTREAM_GAPS; EC2; manter bloqueio de GO. |
| G04 | ALTA | Entradas explícitas no REA direto não têm a aprovação externa ensaiada no protótipo; canário/preload demonstram efeitos e retenção de valores. | FAIL_FOR_UNRESTRICTED_AUTHORITY; EC1; manter bloqueio de GO. |
| G05 | ALTA | EBUSY forçado impede exclusão no prazo; posse/bloqueio/recuperação posterior foram comprovados. Perda/travamento simultâneo dos guardiões e falha total do armazenamento não ensaiados. | FAIL_AT_DEADLINE_AND_UNTESTED_VARIANTS; EC3; manter bloqueio de GO. |
| G06 | ALTA_COM_DADOS_REAIS | Echo/variáveis explícitas podem permanecer na Evidence; todos os sinks/exports/backups e dados reais não foram certificados. | PARTIAL; EC1; manter bloqueio de GO. |
| G07 | ALTA_ANTES_DE_HABILITAR | Native Frida/device/LLDB, provedores/OS reais e runtime browser em OS oficialmente suportado não homologados neste recorte. | NOT_TESTED; EC3; manter bloqueio de GO. |
| G08 | MEDIA_ALTA_OPERACIONAL | CP-R02 socket/rate/concurrency budgets não certificados; origem exata do CP-R05 antigo permanece desconhecida. O SQLITE_BUSY novo foi reproduzido/corrigido, sem provar retroativamente a causa antiga. | NOT_TESTED; EC3; manter bloqueio de GO. |

Os critérios completos EA-14, EA-16, EA-17, EA-18, EA-23, EA-25, EA-26 e EA-28 continuam NOT_TESTED. Ensaios posteriores estreitos de memória/PID/saída, retenção e falha de sink não promovem automaticamente esses critérios completos.

Não entram no plano mínimo: novo IAM/gateway, comandos arbitrários, serviço de assinaturas, exportador de relatórios, biblioteca de credenciais, compatibilidade com todos os sistemas/provedores ou novos ciclos de fault injection. Perda/travamento de guardiões, falha total do armazenamento, clocks, flooding e durabilidade ficam documentados e bloqueiam liberação; novos ensaios exigiriam uma missão posterior delimitada.

Não tentar “fechar” exclusão física/backups desconhecidos com uma alegação genérica: limitar a decisão às cópias controladas e manter a incerteza. RR-04 é PASS para posse/bloqueio/recuperação, mas **FAIL de exclusão no prazo sob o EBUSY forçado**. O FAIL não é apagado pela recuperação tardia.

## Verificação desta consolidação

Verificado por leitura de repositório e registros, comparação de metadados de branch via GitHub, hashes SHA-256 e checagens documentais com Python stdlib. Nenhum código REA foi importado/executado no host. Apenas documentos são alterados nesta rodada. Os hashes dos registros lidos e a estrutura dos dez objetivos estão no [registro JSON](rea-1-1-closeout-matrix-2026-10-16.json).

## Roadmap e próxima ação

REA-0: concluída. REA-1: concluída. REA-1.1: parcial, matriz pronta, EC1/EC2/EC3 pendentes. REA-2/3/4: não iniciadas. Nenhum merge, deploy, publicação de pacote ou integração está autorizado por esta consolidação.

Próxima ação: executar EC1 e preservar o protótipo congelado.

Próximo prompt operacional:

> Execute o EC1 da matriz de encerramento da REA-1.1: revise os 29 workflows e ações locais, entrypoints de instalação/preparação/build, ferramentas MCP e rotas sensíveis, registrando efeitos, autoridade, entradas e sinks. Reaproveite as evidências, classifique lacunas sem ampliar o protótipo ou executar provedores. Preserve a main, sem integração, merge, publicação ou deploy.
