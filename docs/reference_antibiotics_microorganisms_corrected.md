# Исправленный справочник антибиотиков, групп антибиотиков и микроорганизмов

Документ собран на основе:
- эталонного справочника групп антибиотиков;
- эталонного справочника микробных патогенов;
- системного экспортного файла `reference_antibiotics_microorganisms.md`.

Нормализация выполнена **по вашим двум эталонным справочникам**, без дополнительной внешней таксономической валидации.

## Что исправлено

- Удалены служебные и ошибочные значения, которые попали в список как отдельные элементы: например, `I поколение`, `• V поколение`, обрывки строк и служебные комментарии.
- Склеены разрезанные значения: например, `Полимиксин` + `В` → `Полимиксин В`, `Acinetobacter p` + `ittii` → `Acinetobacter pittii`.
- Сокращённые названия родов развёрнуты до полных: `P.`, `M.`, `S.`, `B.`, `C.` → полные латинские названия.
- Для `Corynebacterium` и части грибов убраны авторские подписи, ссылки `[англ.]`, `corrig.` и прочие нецелевые хвосты, чтобы в справочнике остались только названия таксонов.
- ESKAPE-патогены вынесены в отдельные таксономические группы, как это уже было задумано в системном экспорте.
- Удалены точные дубликаты.

> Примечание: коды отдельных антибиотиков и микроорганизмов не сохранялись, потому что в исходном системном файле многие записи были разрезаны или загрязнены служебным текстом. Для интеграции безопаснее использовать нормализованные названия из этого файла.

## Сводка

- Группы антибиотиков: **18**
- Антибиотики: **47**
- Микроорганизмы: **840**
- Таксономические группы микроорганизмов: **5**

## Группы антибиотиков

| Код группы | Название | Количество антибиотиков |
| --- | --- | ---: |
| `ABG-0001` | Пенициллины | 8 |
| `ABG-0002` | Цефалоспорины | 11 |
| `ABG-0003` | Ингибиторозащищенные цефалоспорины | 3 |
| `ABG-0004` | Карбапенемы | 3 |
| `ABG-0005` | Монобактамы | 1 |
| `ABG-0006` | Гликопептиды | 1 |
| `ABG-0007` | Липогликопептиды | 1 |
| `ABG-0008` | Липопептиды | 1 |
| `ABG-0009` | Макролиды | 3 |
| `ABG-0010` | Тетрациклины | 2 |
| `ABG-0011` | Амфениколы | 1 |
| `ABG-0012` | Аминогликозиды | 4 |
| `ABG-0013` | Оксазолидиноны | 1 |
| `ABG-0014` | Анзамицины | 1 |
| `ABG-0015` | Линкозамиды | 2 |
| `ABG-0016` | Глицилциклины | 1 |
| `ABG-0017` | Полимиксины | 2 |
| `ABG-0018` | Производные фосфоновой кислоты | 1 |

## Антибиотики по группам

### 1. Пенициллины (`ABG-0001`)

Количество: **8**

- Бензилпенициллина натриевая соль
- Бензатина бензилпенициллин
- Оксациллин
- Амоксициллин
- Ампициллин
- Пиперациллин
- Амоксициллин+Клавулановая кислота
- Пиперациллин+Тазобактам

### 2. Цефалоспорины (`ABG-0002`)

Количество: **11**

- Цефазолин
- Цефалексин
- Цефуроксим
- Цефуроксим аксетил
- Цефотаксим
- Цефиксим
- Цефтриаксон
- Цефоперазон
- Цефтазидим
- Цефепим
- Цефтаролин

### 3. Ингибиторозащищенные цефалоспорины (`ABG-0003`)

Количество: **3**

- Цефоперазон+сульбактам
- Цефепим+сульбактам
- Цефтазидим+авибактам

### 4. Карбапенемы (`ABG-0004`)

Количество: **3**

- Имипенем
- Меропенем
- Эртапенем

### 5. Монобактамы (`ABG-0005`)

Количество: **1**

- Азтреонам

### 6. Гликопептиды (`ABG-0006`)

Количество: **1**

- Ванкомицин

### 7. Липогликопептиды (`ABG-0007`)

Количество: **1**

- Телаванцин

### 8. Липопептиды (`ABG-0008`)

Количество: **1**

- Даптомицин

### 9. Макролиды (`ABG-0009`)

Количество: **3**

- Эритромицин
- Кларитромицин
- Азитромицин

### 10. Тетрациклины (`ABG-0010`)

Количество: **2**

- Тетрациклин
- Доксициклин

### 11. Амфениколы (`ABG-0011`)

Количество: **1**

- Хлорамфеникол

### 12. Аминогликозиды (`ABG-0012`)

Количество: **4**

- Стрептомицин
- Канамицин
- Гентамицин
- Амикацин

### 13. Оксазолидиноны (`ABG-0013`)

Количество: **1**

- Линезолид

### 14. Анзамицины (`ABG-0014`)

Количество: **1**

- Рифампицин

### 15. Линкозамиды (`ABG-0015`)

Количество: **2**

- Линкомицин
- Клиндамицин

### 16. Глицилциклины (`ABG-0016`)

Количество: **1**

- Тигециклин

### 17. Полимиксины (`ABG-0017`)

Количество: **2**

- Полимиксин В
- Колистиметат натрия

### 18. Производные фосфоновой кислоты (`ABG-0018`)

Количество: **1**

- Фосфомицин

## Микроорганизмы

Микроорганизмы сгруппированы в том виде, который подходит для наполнения выпадающих списков.

Дополнительно рекомендуется сохранить в приложении возможность ручного ввода патогенов, которых нет в этом перечне.

### 1. Грамотрицательные бактерии (ГОБ)

Количество: **119**

- Acinetobacter spp.
- Acinetobacter baylyi
- Acinetobacter bouvetii
- Acinetobacter calcoaceticus
- Acinetobacter gerneri
- Acinetobacter grimontii
- Acinetobacter haemolyticus
- Acinetobacter johnsonii
- Acinetobacter junii
- Acinetobacter lwoffii
- Acinetobacter parvus
- Acinetobacter pittii
- Acinetobacter radioresistens
- Acinetobacter schindleri
- Acinetobacter tandoii
- Acinetobacter tjernbergiae
- Acinetobacter towneri
- Acinetobacter ursingii
- Enterobacter aerogenes
- Enterobacter amnigenus
- Enterobacter arachidis
- Enterobacter asburiae
- Enterobacter bugandensis
- Enterobacter cancerogenous
- Enterobacter cloacae
- Enterobacter cowanii
- Enterobacter dissolvens
- Enterobacter gergoviae
- Enterobacter helveticus
- Enterobacter hormaechei
- Enterobacter intermedius
- Enterobacter kobei
- Enterobacter ludwigii
- Enterobacter mori
- Enterobacter nimipressuralis
- Enterobacter oryzae
- Enterobacter pulveris
- Enterobacter pyrinus
- Enterobacter radicincitans
- Enterobacter taylorae
- Enterobacter turicensis
- Enterobacter soli
- Klebsiella spp.
- Klebsiella aerogenes
- Klebsiella granulomatis
- Klebsiella grimontii
- Klebsiella huaxiensis
- Klebsiella kielensis
- Klebsiella michiganensis
- Klebsiella milletis
- Klebsiella oxytoca
- Klebsiella quasipneumoniae
- Klebsiella quasivariicola
- Klebsiella senegalensis
- Klebsiella steroids
- Klebsiella variicola
- Escherichia coli
- Morganella morganii
- Providencia spp.
- Providencia stuartii
- Providencia sneebia
- Providencia rettgeri
- Providencia rustigianii
- Providencia heimbachae
- Providencia burhodogranariea
- Providencia alcalifaciens
- Proteus spp.
- Proteus hauseri
- Proteus mirabilis
- Proteus myxofaciens
- Proteus penneri
- Proteus vulgaris
- Pseudomonas spp.
- Pseudomonas alcaligenes
- Pseudomonas mendocina
- Pseudomonas pseudoalcaligenes
- Pseudomonas resinovorans
- Pseudomonas putida
- Pseudomonas desmolyticum
- Pseudomonas nitroreducens
- Pseudomonas veronii
- Moraxella spp.
- Moraxella atlantae
- Moraxella boevrei
- Moraxella bovis
- Moraxella bovoculi
- Moraxella canis
- Moraxella caprae
- Moraxella catarrhalis
- Moraxella caviae
- Moraxella cuniculi
- Moraxella equi
- Moraxella lacunata
- Moraxella lincolnii
- Moraxella nonliquefaciens
- Moraxella oblonga
- Moraxella osloensis
- Moraxella pluranimalium
- Moraxella porci
- Moraxella saccharolytica
- Serratia spp.
- Serratia aquatilis
- Serratia entomophila
- Serratia ficaria
- Serratia fonticola
- Serratia glossinae
- Serratia grimesii
- Serratia liquefaciens
- Serratia marcescens
- Serratia myotis
- Serratia nematodiphila
- Serratia odorifera
- Serratia plymuthica
- Serratia proteamaculans
- Serratia quinivorans
- Serratia rubidaea
- Serratia symbiotica
- Serratia ureilytica
- Serratia vespertilionis

### 2. Грамотрицательные бактерии (ГОБ) / ESKAPE

Количество: **4**

- Acinetobacter baumannii
- Enterobacter spp.
- Klebsiella pneumoniae
- Pseudomonas aeruginosa

### 3. Грамположительные бактерии (ГПБ)

Количество: **655**

- Bacillus spp.
- Bacillus cereus
- Bacillus Symun
- Bacillus acidicola
- Bacillus acidiproducens
- Bacillus acidocaldarius
- Bacillus acidoterrestris
- Bacillus aeolius
- Bacillus aerius
- Bacillus aerophilus
- Bacillus agaradhaerens
- Bacillus agri
- Bacillus aidingensis
- Bacillus akibai
- Bacillus albus
- Bacillus alcalophlus
- Bacillus algicola
- Bacillus alginolyticus
- Bacillus alkalidiazotrophicus
- Bacillus alkalinitrilicus
- Bacillus alkalisediminis
- Bacillus alkalitelluris
- Bacillus altitudinis
- Bacillus alveayuensis
- Bacillus alvei
- Bacillus amyloliquefaciens
- Bacillus amyloliquefaciens subsp. amyloliquefaciens
- Bacillus amyloliquefaciens subsp. plantarum
- Bacillus aminovorans
- Bacillus amylolyticus
- Bacillus andreesenii
- Bacillus aneurinilyticus
- Bacillus anthracis
- Bacillus aquimaris
- Bacillus arenosi
- Bacillus arseniciselenatis
- Bacillus arsenicus
- Bacillus aurantiacus
- Bacillus arvi
- Bacillus aryabhattai
- Bacillus asahii
- Bacillus atrophaeus
- Bacillus axarquiensis
- Bacillus azotofixans
- Bacillus azotoformans
- Bacillus badius
- Bacillus barbaricus
- Bacillus bataviensis
- Bacillus beijingensis
- Bacillus benzoevorans
- Bacillus beringensis
- Bacillus berkeleyi
- Bacillus beveridgei
- Bacillus bogoriensis
- Bacillus boroniphilus
- Bacillus borstelensis
- Bacillus brevis
- Bacillus butanolivorans
- Bacillus canaveralius
- Bacillus carboniphilus
- Bacillus cecembensis
- Bacillus cellulosilyticus
- Bacillus centrosporus
- Bacillus chagannorensis
- Bacillus chitinolyticus
- Bacillus chondroitinus
- Bacillus choshinensis
- Bacillus chungangensis
- Bacillus cibi
- Bacillus circulans
- Bacillus clarkii
- Bacillus clausii
- Bacillus coagulans
- Bacillus coahuilensis
- Bacillus cohnii
- Bacillus composti
- Bacillus curdlanolyticus
- Bacillus cycloheptanicus
- Bacillus cytotoxicus
- Bacillus daliensis
- Bacillus decisifrondis
- Bacillus decolorationis
- Bacillus deserti
- Bacillus dipsosauri
- Bacillus drentensis
- Bacillus edaphicus
- Bacillus ehimensis
- Bacillus eiseniae
- Bacillus enclensis
- Bacillus endophyticus
- Bacillus endoradicis
- Bacillus farraginis
- Bacillus fastidiosus
- Bacillus fengqiuensis
- Bacillus filobacterium
- Bacillus firmus
- Bacillus flexus
- Bacillus foraminis
- Bacillus fordii
- Bacillus formosus
- Bacillus fortis
- Bacillus fumarioli
- Bacillus funiculus
- Bacillus fusiformis
- Bacillus gaemokensis
- Bacillus galactophilus
- Bacillus galactosidilyticus
- Bacillus galliciensis
- Bacillus gelatini
- Bacillus gibsonii
- Bacillus ginsengi
- Bacillus ginsengihumi
- Bacillus ginsengisoli
- Bacillus glucanolyticus
- Bacillus gordonae
- Bacillus gottheilii
- Bacillus graminis
- Bacillus halmapalus
- Bacillus haloalkaliphilus
- Bacillus halochares
- Bacillus halodenitrificans
- Bacillus halodurans
- Bacillus halophilus
- Bacillus halosaccharovorans
- Bacillus haynesii
- Bacillus hemicellulosilyticus
- Bacillus hemicentroti
- Bacillus herbersteinensis
- Bacillus horikoshii
- Bacillus horneckiae
- Bacillus horti
- Bacillus huizhouensis
- Bacillus humi
- Bacillus hwajinpoensis
- Bacillus idriensis
- Bacillus indicus
- Bacillus infantis
- Bacillus infernus
- Bacillus insolitus
- Bacillus invictae
- Bacillus iranensis
- Bacillus isabeliae
- Bacillus isronensis
- Bacillus jeotgali
- Bacillus kaustophilus
- Bacillus kobensis
- Bacillus kochii
- Bacillus kokeshiiformis
- Bacillus koreensis
- Bacillus korlensis
- Bacillus kribbensis
- Bacillus krulwichiae
- Bacillus laevolacticus
- Bacillus larvae
- Bacillus laterosporus
- Bacillus lautus
- Bacillus lehensis
- Bacillus lentimorbus
- Bacillus lentus
- Bacillus licheniformis
- Bacillus ligniniphilus
- Bacillus litoralis
- Bacillus locisalis
- Bacillus luciferensis
- Bacillus luteolus
- Bacillus luteus
- Bacillus macauensis
- Bacillus macerans
- Bacillus macquariensis
- Bacillus macyae
- Bacillus malacitensis
- Bacillus mannanilyticus
- Bacillus marisflavi
- Bacillus marismortui
- Bacillus marmarensis
- Bacillus massiliensis
- Bacillus megaterium
- Bacillus mesentericus
- Bacillus mesonae
- Bacillus methanolicus
- Bacillus methylotrophicus
- Bacillus migulanus
- Bacillus mojavensis
- Bacillus mucilaginosus
- Bacillus muralis
- Bacillus murimartini
- Bacillus mycoides
- Bacillus naganoensis
- Bacillus nanhaiensis
- Bacillus nanhaiisediminis
- Bacillus nealsonii
- Bacillus neidei
- Bacillus neizhouensis
- Bacillus niabensis
- Bacillus niacini
- Bacillus novalis
- Bacillus oceanisediminis
- Bacillus odysseyi
- Bacillus okhensis
- Bacillus okuhidensis
- Bacillus oleronius
- Bacillus oryzaecorticis
- Bacillus oshimensis
- Bacillus pabuli
- Bacillus pakistanensis
- Bacillus pallidus
- Bacillus panacisoli
- Bacillus panaciterrae
- Bacillus pantothenticus
- Bacillus parabrevis
- Bacillus paraflexus
- Bacillus pasteurii
- Bacillus patagoniensis
- Bacillus peoriae
- Bacillus persepolensis
- Bacillus persicus
- Bacillus pervagus
- Bacillus plakortidis
- Bacillus pocheonensis
- Bacillus polygoni
- Bacillus polymyxa
- Bacillus popilliae
- Bacillus pseudalcalophilus
- Bacillus pseudofirmus
- Bacillus pseudomycoides
- Bacillus psychrodurans
- Bacillus psychrophilus
- Bacillus psychrosaccharolyticus
- Bacillus psychrotolerans
- Bacillus pulvifaciens
- Bacillus pumilus
- Bacillus purgationiresistens
- Bacillus pycnus
- Bacillus qingdaonensis
- Bacillus qingshengii
- Bacillus reuszeri
- Bacillus rhizosphaerae
- Bacillus rigui
- Bacillus ruris
- Bacillus safensis
- Bacillus salarius
- Bacillus salexigens
- Bacillus saliphilus
- Bacillus schlegelii
- Bacillus sediminis
- Bacillus selenatarsenatis
- Bacillus selenitireducens
- Bacillus seohaeanensis
- Bacillus shacheensis
- Bacillus shackletonii
- Bacillus siamensis
- Bacillus silvestris
- Bacillus simplex
- Bacillus siralis
- Bacillus smithii
- Bacillus soli
- Bacillus solimangrovi
- Bacillus solisalsi
- Bacillus songklensis
- Bacillus sonorensis
- Bacillus sphaericus
- Bacillus sporothermodurans
- Bacillus stearothermophilus
- Bacillus stratosphericus
- Bacillus subterraneus
- Bacillus subtilis
- Bacillus subtilis subsp. inaquosorum
- Bacillus subtilis subsp. spizizenii
- Bacillus subtilis subsp. subtilis
- Bacillus taeanensis
- Bacillus tequilensis
- Bacillus thermantarcticus
- Bacillus thermoaerophilus
- Bacillus thermoamylovorans
- Bacillus thermocatenulatus
- Bacillus thermocloacae
- Bacillus thermocopriae
- Bacillus thermodenitrificans
- Bacillus thermoglucosidasius
- Bacillus thermolactis
- Bacillus thermoleovorans
- Bacillus thermophilus
- Bacillus thermoproteolyticus
- Bacillus thermoruber
- Bacillus thermosphaericus
- Bacillus thiaminolyticus
- Bacillus thioparans
- Bacillus thuringiensis
- Bacillus tianshenii
- Bacillus toyonensis
- Bacillus trypoxylicola
- Bacillus tusciae
- Bacillus validus
- Bacillus vallismortis
- Bacillus vedderi
- Bacillus velezensis
- Bacillus vietnamensis
- Bacillus vireti
- Bacillus vulcani
- Bacillus wakoensis
- Bacillus xiamenensis
- Bacillus xiaoxiensis
- Bacillus zanthoxyli
- Bacillus zhanjiangensis
- Staphylococcus spp.
- Staphylococcus argenteus
- Staphylococcus arlettae
- Staphylococcus agnetis
- Staphylococcus auricularis
- Staphylococcus borealis
- Staphylococcus caeli
- Staphylococcus capitis
- Staphylococcus caprae
- Staphylococcus carnosus
- Staphylococcus caseolyticus
- Staphylococcus chromogenes
- Staphylococcus cohnii
- Staphylococcus cornubiensis
- Staphylococcus condimenti
- Staphylococcus debuckii
- Staphylococcus delphini
- Staphylococcus devriesei
- Staphylococcus edaphicus
- Staphylococcus epidermidis
- Staphylococcus equorum
- Staphylococcus felis
- Staphylococcus fleurettii
- Staphylococcus gallinarum
- Staphylococcus haemolyticus
- Staphylococcus hominis
- Staphylococcus hyicus
- Staphylococcus intermedius
- Staphylococcus jettensis
- Staphylococcus kloosii
- Staphylococcus leei
- Staphylococcus lentus
- Staphylococcus lugdunensis
- Staphylococcus lutrae
- Staphylococcus lyticans
- Staphylococcus massiliensis
- Staphylococcus microti
- Staphylococcus muscae
- Staphylococcus nepalensis
- Staphylococcus pasteuri
- Staphylococcus petrasii
- Staphylococcus pettenkoferi
- Staphylococcus piscifermentans
- Staphylococcus pseudintermedius
- Staphylococcus pseudolugdunensis
- Staphylococcus pulvereri
- Staphylococcus rostri
- Staphylococcus saccharolyticus
- Staphylococcus saprophyticus
- Staphylococcus schleiferi
- Staphylococcus schweitzeri
- Staphylococcus sciuri
- Staphylococcus simiae
- Staphylococcus simulans
- Staphylococcus singaporensis
- Staphylococcus stepanovicii
- Staphylococcus succinus
- Staphylococcus vitulinus
- Staphylococcus warneri
- Staphylococcus xylosus
- Staphylococcus Westin
- Streptococcus spp.
- Streptococcus acidominimus
- Streptococcus agalactiae
- Streptococcus alactolyticus
- Streptococcus anginosus
- Streptococcus australis
- Streptococcus caballi
- Streptococcus cameli
- Streptococcus canis
- Streptococcus caprae
- Streptococcus castoreus
- Streptococcus constellatus
- Streptococcus criceti
- Streptococcus cristatus
- Streptococcus cuniculi
- Streptococcus danieliae
- Streptococcus dentasini
- Streptococcus dentiloxodontae
- Streptococcus dentirousetti
- Streptococcus devriesei
- Streptococcus didelphis
- Streptococcus downei
- Streptococcus dysgalactiae
- Streptococcus entericus
- Streptococcus equi
- Streptococcus equinus
- Streptococcus faecalis
- Streptococcus ferus
- Streptococcus gallinaceus
- Streptococcus gallolyticus
- Streptococcus gordonii
- Streptococcus halichoeri
- Streptococcus halotolerans
- Streptococcus henryi
- Streptococcus himalayensis
- Streptococcus hongkongensis
- Streptococcus hyointestinalis
- Streptococcus hyovaginalis
- Streptococcus ictaluri
- Streptococcus infantarius
- Streptococcus infantis
- Streptococcus iniae
- Streptococcus intermedius
- Streptococcus lactarius
- Streptococcus loxodontisalivarius
- Streptococcus lutetiensis
- Streptococcus macacae
- Streptococcus marimammalium
- Streptococcus marmotae
- Streptococcus massiliensis
- Streptococcus merionis
- Streptococcus minor
- Streptococcus mitis
- Streptococcus moroccensis
- Streptococcus mutans
- Streptococcus oralis
- Streptococcus oricebi
- Streptococcus oriloxodontae
- Streptococcus orisasini
- Streptococcus orisratti
- Streptococcus orisuis
- Streptococcus ovis
- Streptococcus panodentis
- Streptococcus pantholopis
- Streptococcus parasanguinis
- Streptococcus parasuis
- Streptococcus parauberis
- Streptococcus peroris
- Streptococcus pharyngis
- Streptococcus phocae
- Streptococcus pluranimalium
- Streptococcus plurextorum
- Streptococcus pneumoniae
- Streptococcus porci
- Streptococcus porcinus
- Streptococcus porcorum
- Streptococcus pseudopneumoniae
- Streptococcus pseudoporcinus
- Streptococcus pyogenes
- Streptococcus ratti
- Streptococcus rifensis
- Streptococcus rubneri
- Streptococcus rupicaprae
- Streptococcus salivarius
- Streptococcus saliviloxodontae
- Streptococcus sanguinis
- Streptococcus sinensis
- Streptococcus sobrinus
- Streptococcus suis
- Streptococcus tangierensis
- Streptococcus thermophilus
- Streptococcus thoraltensis
- Streptococcus tigurinus
- Streptococcus troglodytae
- Streptococcus troglodytidis
- Streptococcus uberis
- Streptococcus urinalis
- Streptococcus ursoris
- Streptococcus vestibularis
- Streptococcus zooepidemicus
- Viridans streptococci (Streptococcus anginosus group)
- Enterococcus spp.
- Enterococcus avium
- Enterococcus casseliflavus
- Enterococcus durans
- Enterococcus faecalis
- Enterococcus raffinosus
- Enterococcus solitarius
- Clostridium spp.
- Clostridium botulinum
- Clostridium perfringens
- Clostridium tetani
- Clostridium difficile
- Clostridium histolyticum
- Clostridium sordellii
- Corynebacterium spp.
- Corynebacterium accolens
- Corynebacterium afermentans
- Corynebacterium alimapuense
- Corynebacterium alkanolyticum
- Corynebacterium ammoniagenes
- Corynebacterium amycolatum
- Corynebacterium anserum
- Corynebacterium appendicis
- Corynebacterium aquatimens
- Corynebacterium aquilae
- Corynebacterium argentoratense
- Corynebacterium asperum
- Corynebacterium atrinae
- Corynebacterium atypicum
- Corynebacterium aurimucosum
- Corynebacterium auris
- Corynebacterium auriscanis
- Corynebacterium belfantii
- Corynebacterium beticola
- Corynebacterium bouchesdurhonense
- Corynebacterium bovis
- Corynebacterium callunae
- Corynebacterium camporealensis
- Corynebacterium canis
- Corynebacterium capitovis
- Corynebacterium casei
- Corynebacterium caspium
- Corynebacterium choanae
- Corynebacterium ciconiae
- Corynebacterium comes
- Corynebacterium confusum
- Corynebacterium coyleae
- Corynebacterium crudilactis
- Corynebacterium cystitidis
- Corynebacterium defluvii
- Corynebacterium dentalis
- Corynebacterium deserti
- Corynebacterium diphtheriae
- Corynebacterium doosanense
- Corynebacterium durum
- Corynebacterium efficiens
- Corynebacterium endometrii
- Corynebacterium epidermidicanis
- Corynebacterium faecale
- Corynebacterium falsenii
- Corynebacterium felinum
- Corynebacterium flavescens
- Corynebacterium fournieri
- Corynebacterium frankenforstense
- Corynebacterium freiburgense
- Corynebacterium freneyi
- Corynebacterium gerontici
- Corynebacterium glaucum
- Corynebacterium glucuronolyticum
- Corynebacterium glutamicum
- Corynebacterium glyciniphilum
- Corynebacterium gottingense
- Corynebacterium guangdongense
- Corynebacterium haemomassiliense
- Corynebacterium halotolerans
- Corynebacterium hansenii
- Corynebacterium heidelbergense
- Corynebacterium hindlerae
- Corynebacterium humireducens
- Corynebacterium ihumii
- Corynebacterium ilicis
- Corynebacterium imitans
- Corynebacterium incognitum
- Corynebacterium jeddahense
- Corynebacterium jeikeium
- Corynebacterium kalinowskii
- Corynebacterium kefirresidentii
- Corynebacterium kroppenstedtii
- Corynebacterium kutscheri
- Corynebacterium lactis
- Corynebacterium lactofermentum
- Corynebacterium jeikliangguodongiiium
- Corynebacterium lipophiloflavum
- Corynebacterium lizhenjunii
- Corynebacterium lowii
- Corynebacterium lubricantis
- Corynebacterium lujinxingii
- Corynebacterium macginleyi
- Corynebacterium marinum
- Corynebacterium maris
- Corynebacterium massiliense
- Corynebacterium mastitidis
- Corynebacterium matruchotii
- Corynebacterium minutissimum
- Corynebacterium mucifaciens
- Corynebacterium mustelae
- Corynebacterium mycetoides
- Corynebacterium nasicanis
- Corynebacterium neomassiliense
- Corynebacterium nuruki
- Corynebacterium occultum
- Corynebacterium oculi
- Corynebacterium otitidis
- Corynebacterium pacaense
- Corynebacterium parakroppenstedtii
- Corynebacterium parvulum
- Corynebacterium pelargi
- Corynebacterium phocae
- Corynebacterium phoceense
- Corynebacterium pilbarense
- Corynebacterium pilosum
- Corynebacterium pollutisoli
- Corynebacterium propinquum
- Corynebacterium provencense
- Corynebacterium pseudodiphtheriticum
- Corynebacterium pseudokroppenstedtii
- Corynebacterium pseudopelargi
- Corynebacterium pseudotuberculosis
- Corynebacterium pyruviciproducens
- Corynebacterium qintianiae
- Corynebacterium renale
- Corynebacterium resistens
- Corynebacterium riegelii
- Corynebacterium rouxii
- Corynebacterium sanguinis
- Corynebacterium segmentosum
- Corynebacterium senegalense
- Corynebacterium silvaticum
- Corynebacterium simulans
- Corynebacterium singulare
- Corynebacterium sphenisci
- Corynebacterium spheniscorum
- Corynebacterium sputi
- Corynebacterium stationis
- Corynebacterium striatum
- Corynebacterium suicordis
- Corynebacterium sundsvallense
- Corynebacterium suranareeae
- Corynebacterium tapiri
- Corynebacterium terpenotabidum
- Corynebacterium testudinoris
- Corynebacterium thomssenii
- Corynebacterium timonense
- Corynebacterium trachiae
- Corynebacterium tuberculostearicum
- Corynebacterium tuscaniense
- Corynebacterium uberis
- Corynebacterium ulcerans
- Corynebacterium ulceribovis
- Corynebacterium urealyticum
- Corynebacterium ureicelerivorans
- Corynebacterium urinapleomorphum
- Corynebacterium urinipleomorphum
- Corynebacterium urogenitale
- Corynebacterium uropygiale
- Corynebacterium uterequi
- Corynebacterium variabile
- Corynebacterium vitaeruminis
- Corynebacterium wankanglinii
- Corynebacterium xerosis
- Corynebacterium yudongzhengii
- Corynebacterium zhongnanshanii
- Listeria spp.
- Listeria aquatica
- Listeria booriae
- Listeria cornellensis
- Listeria fleischmannii
- Listeria grandensis
- Listeria grayi
- Listeria innocua
- Listeria ivanovii
- Listeria marthii
- Listeria monocytogenes
- Listeria newyorkensis
- Listeria riparia
- Listeria rocourtiae
- Listeria seeligeri
- Listeria weihenstephanensis
- Listeria welshimeri

### 4. Грамположительные бактерии (ГПБ) / ESKAPE

Количество: **2**

> Для `Staphylococcus aureus` дополнительно имеет смысл отдельно подсветить `MRSA` как особо важный вариант.

- Staphylococcus aureus
- Enterococcus faecium

### 5. Микромицеты

Количество: **60**

> Другие редкие грибы можно оставить для ручного ввода, как и было указано в исходном эталонном документе.

- Candida spp.
- Candida albicans
- Candida ascalaphidarum
- Candida amphixiae
- Candida antarctica
- Candida atlantica
- Candida atmosphaerica
- Candida auris
- Candida blankii
- Candida blattae
- Candida bracarensis
- Candida bromeliacearum
- Candida carpophila
- Candida catenulata
- Candida cerambycidarum
- Candida chauliodes
- Candida corydali
- Candida dosseyi
- Candida dubliniensis
- Candida ergatensis
- Candida fructus
- Candida glabrata
- Candida guilliermondii
- Candida fermentati
- Candida haemulonii
- Candida humilis
- Candida insectamens
- Candida insectorum
- Candida intermedia
- Candida jeffresii
- Candida kefyr
- Candida keroseneae
- Candida krusei
- Candida lusitaniae
- Candida lyxosophila
- Candida maltosa
- Candida marina
- Candida membranifaciens
- Candida milleri
- Candida mogii
- Candida oleophila
- Candida oregonensis
- Candida parapsilosis
- Candida quercitrusa
- Candida rhizophoriensis
- Candida rugosa
- Candida sake
- Candida sharkiensis
- Candida shehatea
- Candida temnochilae
- Candida tenuis
- Candida theae
- Candida tropicalis
- Candida tsuchiyae
- Candida sinolaborantium
- Candida sojae
- Candida viswanathii
- Candida ubatubensis
- Candida utilis
- Candida zemplinina

## Итог по сравнению с исходным системным экспортом

- Антибиотики: **51 → 47**
- Микроорганизмы: **980 → 840**
- Основные причины уменьшения количества: удаление ложных элементов, склейка разрезанных строк, удаление дублей и очистка комментариев/авторских подписей.
