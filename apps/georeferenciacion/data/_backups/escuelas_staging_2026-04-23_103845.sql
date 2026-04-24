-- Backup de escuelas_staging generado por import_03_escuelas.py
-- Fecha: 2026-04-23_103845
-- Filas: 242

BEGIN;

CREATE TABLE IF NOT EXISTS escuelas_staging (
    nombre    TEXT,
    tipo      TEXT,
    latitud   TEXT,
    longitud  TEXT,
    direccion TEXT
);

INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('TORRES DE VILLA ALSACIA', '1', '4.64382475567346', '-74.1254976443358', 'CALLE 12 C # 71 C - 30');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('COLEGIO SAN JOSE', '1', '4.6167934997773', '-74.1661250756755', 'CALLE 46A SUR # 78N - 41');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('SUPER MANZANA 2', '1', '4.61654532371613', '-74.1967840891662', 'CARRERA 73 BIS SUR # 26 - 81');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('GRUPO CARVAJAL VIVE DIGITAL', '1', '4.61430765289906', '-74.1425933603298', 'CALLE 37B SUR # 72J - 74');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('COLEGIO EDUARDO UMAÑA LUNA', '1', '4.64171498737681', '-74.1747292045118', 'CRA. 93A # 42-42');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('FUNDACIÓN LEONOR HERNANDEZ', '1', '4.64756533796547', '-74.1673821667979', 'CL. 26sur # 93-40 SALÓN COMUNAL');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('SALÓN COMUNAL VILLA DE LA TORRE', '1', '4.62675656674708', '-74.1668998026571', 'CRA. 81G #42B-58 sur');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('FUNDACIÓN REAL PRIMAVERA', '1', '4.64420039950868', '-74.1652593775303', 'Calle 26 SUR # 89D - 79');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('SALÓN COMUNAL UNIR 1', '1', '4.64213826820016', '-74.1669302621846', 'CL. 35 sur # 89D-32');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('SALÓN COMUNAL LUCERNA', '1', '4.611898406861449', '-74.1455502756755', 'Calle 38C Sur # 72K - 33');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('COLEGIO FRANCISCO MIRANDA', '1', '4.61347232427476', '-74.1524334621847', 'CARRERA 73 BIS # 40-55');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('LA MACARENA', '1', '4.61981188700929', '-74.1488866891661', 'CARRERA 73D # 37-29 SUR');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('LICEO PIÑEROS CORTES', '1', '4.62492872219021', '-74.1434090045118', 'CALLE 2 BIS # 73C - 55');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('JAC AMÉRICAS OCCIDENTAL', '1', '4.62875847226292', '-74.1393237468389', 'CALLE 5A # 72A20');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('JAC ONASIS', '1', '4.6152647120479', '-74.1635480891662', 'AVE 1 DE MAYO # 43-76');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('CASA DE IGUALDAD DE OPORTUNIDADES PARA LAS MUJERES', '1', '4.62639962192221', '-74.1348461045118', 'CALLE 3 A # 71 A - 54');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('FUNDACION MARTA CHACON', '1', '4.63256839595097', '-74.134842635203', 'CALLE 7A # 71B - 65');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('JAC CLASS', '1', '4.6154673762872', '-74.1777247468391', 'CALLE 57 B SUR # 80H - 32');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('SALÓN COMUNAL BOITA', '1', '4.6025280020863', '-74.1527259001504', 'Cl. 48b Sur #13, Bogotá');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('SALÓN COMUNAL RIVERAS DE OCCIDENTE PRIMER SECTOR', '1', '4.64364785497497', '-74.167712365518', 'Cra 91 calle 34 b sur');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('SALON COMUNAL CALIFORNIA', '1', '4.61878369328263', '-74.1493104078485', 'Cl. 38b Sur #73C - 86');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('CASA 1L YORUBA', '1', '4.62121307453929', '-74.1522989231881', 'Cl. 38b Sur #78b-31, Bogotá');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('SALÓN COMUNAL PALMITAS', '1', '4.60393181443716', '-74.1379797366836', 'CL 38 C SUR Cra. 101A 15');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('LA IGUALDAD', '1', '4.62131954464022', '-74.1274261099211', 'Cra 68c # 2A sur 84');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('CENTRO 1L BIBLIOTECA BRITALIA', '1', '4.6234171920897', '-74.1777437213437', ' Calle 52AS #52A-08 Sur');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('ASOCIACION FRATERNIDAD DE ABUELOS ENRIQUE GROSSE', '1', '4.62452739180369', '-74.1689087808578', 'Cra. 81c Bis A #43-24');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('BIBLIOTECA LA GUARICHA', '1', '4.62106121104952', '-74.1739706748143', 'Calle 52 A Sur ·52 A -08 sur');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('URBANIZACIÓN CATANIA', '1', '4.635490063955969', '-74.1482652096926', 'CRA 79B # 6B-65');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('CASA LGBTIQ+', '1', '4.62539660378548', '-74.1531189366833', 'CL 36 SUR # 78K 58');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('SALON COMUNAL LAS MARGARITAS 1', '1', '4.63452578922484', '-74.1770206925088', 'KR 89A # 45A 38 SUR');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('SALON COMUNAL LOS PERIODISTAS', '1', '4.61697779838934', '-74.1577537004896', 'Calle 41B # 78H - 45 Sur');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('SUPER MANZANA 12', '1', '4.63326178955117', '-74.153994194353', 'DIAGONAL 2B # 79H 08');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('VILLA ALSACIA', '1', '4.64313525071875', '-74.1292728790133', 'Cl. 12a #71C-61, Bogotá Mirador de Castilla 3');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('SALÓN COMUNAL MARIA PAZ', '1', '4.6370823011237', '-74.1580137771691', 'CL 5A SUR # 82 63');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('CDC BRITALIA', '1', '4.62188759853348', '-74.1648405213437', 'AV CR 80 # 43-43');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('SALON COMUNAL PALENQUE', '1', '4.61536795845542', '-74.1585938213439', 'CRA 78D BIS # 41G-15 SUR');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('FUNDACIÓN PT', '1', '4.63437340174133', '-74.1664515501785', 'Cra. 86g #40-60');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('SALON COMUNAL CASTILLA', '1', '4.63798086316172', '-74.1416312790134', 'CRA 78 # 7F - 20');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('ROMA 4', '2', '4.60752850783446', '-74.1725491071548', 'CARRERA 78 57C SUR');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('GRUPO 1 IED VILLA RICA', '1', '4.60038494647966', '-74.178379321344', 'CRA. 77 K BIS No. 50 -26');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('GRUPO 3 JOVENES BRITALIA', '1', '4.62404927368048', '-74.1725622213437', 'CRA 81 J No. 47B - 16');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('GRUPO 4 RODRIGO UMAÑA LUNA', '1', '4.64139642552086', '-74.1747388636737', 'CRA 93 CON CALLE 42B SUR');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('GRUPO 5 IED LA FLORESTA SUR', '1', '4.62079830483107', '-74.1266500925089', 'CRA 68 A BIS SUR 1 - 09');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('GRUPO 6 CASTILLA IED SAN JOSE DE CASTILLA', '1', '4.63741911935792', '-74.1426767520228', 'CALLE 7 C No. 78 - 20');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('2 FUCOLPRAV', '1', '4.6221836621383', '-74.1600248060042', 'Carrera 79b N° 41b-34 sur');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('IED LAS AMERICAS', '1', '4.61703771166243', '-74.1508150925089', 'Cra. 73c Bis # 38C-84S');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('NAN', '1', '4.61351058279217', '-74.1777677078485', 'CARERA 80I # 57B-50 SUR');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('IED MANUEL CEPEDA VARGAS', '1', '4.61687825793048', '-74.1779682096927', 'Calle 56 sur N° 81-26');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('SALON COMUNAL LAGOS DE CASTILLA', '1', '4.64795164064839', '-74.1422530925086', 'CRA 80 F # 10D - 01');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('SALÓN SOCIAL Y DE DESARROLLO COMUNITARIO LA MARIA', '1', '4.62200948640073', '-74.1655986520229', 'CRA 80 j # 42 F-33');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('SALON COMUNAL SUPER MANZANA 6', '1', '4.61980571107539', '-74.1495621943531', 'CALLE 38 # 73f-05');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('COLEGIO ALQUERÍA LA FRAGUA', '1', '4.60515710258188', '-74.1361370078486', 'CL 37 B SUR # 68 D 93');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('SALÓN COMUNAL CARVAJAL TECHO', '1', '4.61391774710242', '-74.1398824790136', 'CL 37 # 70B - 05');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('COLEGIO SAN RAFAEL', '1', '4.61765437561618', '-74.1615477808578', 'Cl. 42b Sur #78i-46');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('PVD CARVAJAL', '1', '4.61430765288945', '-74.1426791943532', 'CALLE 37B SUR # 72J - 74');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('COLEGIO MARSELLA', '1', '4.63322548333959', '-74.1272655790134', 'CRA 69 # 8-65');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('SALÓN COMUNAL MORABIA', '1', '4.60586347917829', '-74.153387580858', 'CL 43 SUR # 72 14');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('SALÓN COMUNAL RIVERAS DE OCCIDENTE', '1', '4.64354826669594', '-74.1681584917193', 'CL 35 A SUR # 92B 21');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('SALÓN COMUNAL FLORALIA', '1', '4.59663261032487', '-74.1417221808304', 'TV 68C # 31 26');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('SALÓN COMUNAL UNIR', '1', '4.64222059360958', '-74.1659378519949', 'CL 34A SUR # 89C 08');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('RESERVADO ROMA II', '1', '4.61600129488892', '-74.1807768227978', 'CALLE 57C SUR 81D-01');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('ALCALDÍA LOCAL DE KENNEDY', '1', '4.61988625690024', '-74.1577958366543', 'TV 78K # 89C 08');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('CDC BELLAVISTA', '1', '4.64580359914866', '-74.1717503519948', 'CALLE 38 SUR # 94C 29');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('JAC EL RUBI', '1', '4.60943365467135', '-74.1756577366544', 'CL 57H SUR # 78M 44');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('I.E.D JACKELINE', '1', '4.6090032899571', '-74.1629830096654', 'CARRERA 77Q CLL 46 SUR');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('JARDIN  BAMBI DEL BIENESTAR FAMILIAR', '1', '4.64342229969264', '-74.1725513348079', 'CARRERA 93B 40A 20 SUR');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('CASA DE LA JUVENTUD IWOKA', '1', '4.62304693760222', '-74.1563432213136', 'CARRERA 78N 39-33');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('COLEGIO CASTILLA IED', '1', '4.64076556862375', '-74.1419436808301', 'KR 78C # 8A 43');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('JAC TUNDAMA', '1', '4.60283556282096', '-74.1500779366544', 'CALLE 46 SUR # 72I-06');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('COLEGIO CARLOS ARTURO TORRES SEDE B', '1', '4.59983196386168', '-74.1464851096655', 'TV 72B # 44C 19 SUR');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('JAC VISIÓN COLOMBIA', '1', '4.65076623315056', '-74.1352990213134', 'KR 79C#13A-36');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('JARDIN INFANTIL APRENDIENDO JUNTOS ABC', '1', '4.6507681187499', '-74.1590076687099', 'CRA 90 C  CALLE 6A');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('COLEGIO FLORESTA SUR SEDE B', '1', '4.620290710988369', '-74.1267584654894', 'Cra. 68a Bis #01-09');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('PLAZA DE CORABASTOS', '1', '4.627729248401129', '-74.1618369950256', 'Cra. 80 #40 55 Sur');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('FUNDACIÓN FAPAZ - SALÓN SOCIAL OIKOS III 2 ETAPA', '1', '4.61643078587981', '-74.1470182423296', 'CALLE 38 #72Q - 53');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('SALON COMUNAL LAS LUCES', '1', '4.60566244020551', '-74.1676179401279', 'CRA 77H # 51A-84 SUR');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('SALÓN COMUNAL VILLA ALSACIA', '1', '4.64375236133559', '-74.1360713348079', 'CALLE 11A # 72D-20');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('JAC FLORALIA', '1', '4.59675024791785', '-74.1416148924786', 'TV. 68C SUR #31-26');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('SALON COMUNAL VILLA CLAUDIA', '1', '4.61734982357606', '-74.1291009943247', 'CALLE 9A SUR #68F-23');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('CEDE C TIMIZA', '1', '4.61113261881773', '-74.1567063501488', 'CARRERA 74 # 42GSUR - 52');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('ALCALDIA LOCAL KENNEDY', '1', '4.61912329321112', '-74.1577663943247', 'CALLE 41B SUR # 78J-50');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('ANDARES', '1', '4.63264303382328', '-74.1368732961707', 'CRA 71 G #  6D-22');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('GRUPO CARIMAGUA', '1', '4.60985336038675', '-74.1469612654896', 'CRA 72 K # 39 SUR - 24');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('NAN', '1', '4.62586811591474', '-74.1393510348081', 'AC 3 # 72-99');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('BIBLIOTECA COMUNITARIA ALTAMAR', '1', '4.63533464526522', '-74.172260834808', 'CL 42F SUR # 88C 20');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('ASOCIACION MUJERES DEL RIO', '1', '4.64624826053833', '-74.1735537501486', 'CALLE 40 SUR # 96-04');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('PUNTO VIVE DIGITAL CARVAJAL', '1', '4.64126955165242', '-74.1723855424876', 'CRA.91B #41-18');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('PARQUE LAS PISCINAS', '2', '4.64141305572235', '-74.1644460053815', 'Dg. 34 Bis Sur, Kennedy, Bogotá');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('MUNDO AVENTURA 1', '2', '4.62215947425278', '-74.1348344305173', 'Cra. 71d #1-14 Sur, Bogotá');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('MUNDO AVENTURA 2', '2', '4.62215947425278', '-74.1348344305173', 'Cra. 71d #1-14 Sur, Bogotá');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('AYACUCHO', '2', '4.628991296810129', '-74.1504928881886', 'CALLE 6 SUR 78M 55');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('VILLA ALSACIA
SALON COMUNAL', '2', '4.64314213092791', '-74.1350416358909', 'CALLE 11A #72-72');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('DELICIAS SAUCOS DEL BOSQUE', '2', '4.5993213811508', '-74.1484416629412', 'CALLE 45 SUR 72 B 17');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('PARQUE VALLADOLID', '2', '4.64551653980184', '-74.1469135711638', 'CARRERA 81D CON CALLE 8 B');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('VILLA CLAUDIA', '2', '4.61774849953641', '-74.1266379610878', 'CALLE 9 A SUR # 68 - 05');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('TORRES DE NUEVO CASTILLA 1 CALANDAIMA
OPERADOR', '2', '4.64934450299778', '-74.1519005306895', 'CALLE 8 # 88B 90 SUR');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('CARIMAGUA 1ER SECTOR', '2', '4.61073728358833', '-74.1458725169069', 'Calle 39 Sur # 72 K 02');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('TINTAL II', '2', '4.64976320469968', '-74.1619367322515', 'Calle 6 Bis # 90 A 80 Torres de Tintala 2');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('RIVERAS DE OCCIDENTE ACUERDO FDLK', '2', '4.6434404', '-74.1682472', 'Calle 35A # 92B - 21');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('BOITA', '2', '4.60260985135844', '-74.1526285053011', 'CALLE 48B SUR # 72K - 13');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('SUPER 7 ALK', '2', '4.62507686726361', '-74.1494918071547', 'CARRERA 78D · 35 18 SUR');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('BELLA VISTA DINDALITO', '2', '4.64510196989678', '-74.1742966610565', 'CALLE 42 SUR # 94B-15');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('SALONCOMUNAL BARRIO JACKELINE', '2', '4.60947546049386', '-74.1625981206461', 'CALLE 45 A SUR 77 Q - 51');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('CAMILO TORRES', '2', '4.617342', '-74.1476199', 'DIAGONAL 37D SUR CON CARRERA 73 A BIS');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('CASA BLANCA', '2', '4.6178490156735', '-74.1477127476286', 'CALLE 47B SUR # 15');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('GIRALDILLA 1ER SECTOR', '2', '4.6134361005722', '-74.1654680899563', 'CARRERA 78G BIS # 47B 24 SUR');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('IGLESIA SAN JUAN DE LA CRUZ', '2', '4.62042293385362', '-74.1631765420413', 'CARRERA 79B # 42C 26 SUR');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('SUPER MANZANA 6 PRIORIZADO FDLK', '2', '4.61952268175683', '-74.1502747702335', 'CALLE 38 D SURCON TRANSVERSAL 73F');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('PARQUES DE CASTILLA 4', '2', '4.64574147349629', '-74.1396482783185', 'CARRERA 79 # 10D 95');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('PARQUE MARGARITAS 
CARMELO', '2', '4.62530903058812', '-74.1727201783185', 'CALLE 47 A SUR # 82');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('NUEVA CASTILLA', '2', '4.65189877171467', '-74.1512944918097', 'CALLE 88D ·# 8C 21');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('NUEVA MARSELLA
PARQUE EL TRIANGULO', '2', '4.62311219216003', '-74.1437702476286', 'TRANSVERSAL 73B BIS· 2');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('ANDA LUCIA', '2', '4.65441980369662', '-74.1364860629734', 'CALLE 15 A # 81 - 71');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('PARQUE LA MAGDALENA 2', '2', '4.65444009060633', '-74.1586321494821', 'CARRERA 94 ESQUINA CALLE 7, KENNEDY BOGOTA');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('PARQUE DINDALITO BELLAVISTA', '2', '4.64427864198076', '-74.1747042764647', 'CALLE 42 SUR # 94B-15');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('PIO XII', '2', '4.63613877000541', '-74.1504143899562', 'CALLE 6 B # 79 c 81');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('RIVERAS DE OCCIDENTE', '2', '4.64346646189388', '-74.1683174662717', 'CARRERA 91 BIS #35A SUR');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('PARQUE CASTILLA', '2', '4.63854547595339', '-74.1455064472459', 'CALLE. 7a Bis C #78h29');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('LICEO PIÑEROS CORTES', '2', '4.62502340386214', '-74.1434219783184', 'Cl. 2 Bis #73c55, Bogotá');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('COLEGIO INEM', '2', '4.62537260988548', '-74.1559124476287', 'Calle 38c Sur #79-08 a, Cl. 38c Sur #78p-2, Kennedy, Bogotá');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('PARQUE PRINCIPAL TECHO', '2', '4.62624688523689', '-74.1473038476287', 'CARRERA. 78B #06 SUR-05,');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('CATALINA 1', '2', '4.60999547205289', '-74.1697543053011', 'CARRERA 77 V BIS A 54 A SUR');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('VALENCIA BOMBAY', '2', '4.60848010671103', '-74.1447511490731', 'CALLE 39 b SUR #72h-28');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('PARQUE LA MAGDALENA 2', '2', '4.65445078408428', '-74.1586106937033', 'CARRERA 94 ESQUINA CALLE 7, KENNEDY BOGOTA');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('UNIR 1 JORNADA TARDE', '2', '4.64534394161545', '-74.1674314225396', 'CARRERA 91C # 34 SUR');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('GILMA JIMENEZ', '2', '4.62318147395839', '-74.1757359937035', 'CALLE 51 A SUR N 82 A 16');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('BELLA VISTA DINDALITO MENORES JORNADA MAÑANA', '2', '4.64418239951824', '-74.1746828206863', 'CALLE 42 SUR # 94B-15');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('BELLA VISTA DINDALITO MENORES A', '2', '4.64425725478621', '-74.1746828206863', 'CALLE 42 SUR # 94B-15');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('BELLA VISTA DINDALITO MAYORES A', '2', '4.64424656117699', '-74.1747471937035', 'CALLE 42 SUR # 94B-15');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('PARQUE TIMIZA CANCHA FUTBOL 8', '2', '4.61009016030375', '-74.1533833225398', 'Cl. 40h Sur #72r, Bogotá');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('PARQUE LA ALEJANDRA', '2', '4.60579843673233', '-74.1483043441809', 'Cra. 72 I # a, Bogotá');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('PARQUE VILLA DE LOS SAUCES', '2', '4.60520359098878', '-74.175760707195', NULL);
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('PARQUE LAS LUCES VILLA RICA', '2', '4.60614847910738', '-74.1685426783588', 'CALLE 52A SUR #77K BIS');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('PARQUE LAS LUCES VILLA RICA', '2', '4.60614847910738', '-74.1685426783588', 'CALLE 52A SUR #77K BIS');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('AMERICAS OCCIDENTAL', '2', '4.62154959863051', '-74.1398638225397', 'Cl. 2a Sur # 72-70');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('UNIR 1 JORNADA MAÑANA', '2', '4.64534394161545', '-74.1673026765052', 'CARRERA 91C # 34 SUR');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('PARQUE LINEAL NUEVA CASTILLA JUVENILES', '2', '4.65130625892053', '-74.1512399053413', 'Ak 88d #8C-21, Kennedy, Bogotá');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('PARQUE DESARROLLO VILLA ANDRES', '2', '4.63766996327598', '-74.1679280071948', 'CARRERA 88 C BIS # 40 A SUR');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('CAYETANO CAÑIZARES', '2', '4.62683028581071', '-74.1615536410799', 'Cra. 80 #40 55 Sur, Bogotá');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('CARVAL CAMPO DE FUTBOL
ADMI', '2', '4.61535861682529', '-74.1355671090484', 'Cl. 25 Sur #69c-2, Bogotá');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('BELLA VISTA DINDALITO MENORES B', '2', '4.64422517395805', '-74.1747579225397', 'CALLE 42 SUR # 94B-15');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('BELLA VISTA DINDALITO MAYORES B', '2', '4.64422517395805', '-74.1747579225397', 'CALLE 42 SUR # 94B-15');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('BELLA VISTA DINDALITO MAYORES JORNADA MAÑANA', '2', '4.64422517395805', '-74.1747579225397', 'CALLE 42 SUR # 94B-15');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('PARQUE LEONARD EULER
GRUPO FEMENINO', '2', '4.64014425616158', '-74.1695580937035', 'Cra. 77q #53-14, Kennedy, Bogotá');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('CONTRAUNIDOS', '2', '4.64070170031301', '-74.159557136031', 'CALLE. 2 # 87-15 SUR,');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('VILLA NUEVA', '2', '4.60282465706229', '-74.1400991937036', 'CALLE 39D Sur No  68G-80');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('CALIFORNIA CENTRAL', '2', '4.61909337519593', '-74.1490425783587', 'CARRERA 73D · 10');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('PARQUE UNIR 1 
JORNADA TARDE', '2', '4.64235051265595', '-74.1669044225396', 'CARRERA 89D # 1A -75SUR');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('ANDA LUCIA 1', '2', '4.65420441222831', '-74.1393049648672', 'CALLE 13D # 82 A');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('TINTALITO', '2', '4.63065865314761', '-74.1707508071949', 'CALLE. 42G Sur # 86C-10');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('ROMA 4', '2', '4.61170294679206', '-74.170302955819', 'CALLE 53 B SUR # 78J BIS 34');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('GRAN BRITALIA', '2', '4.62296308009012', '-74.1700213918502', 'Cl. 46 Sur # 81B - 24, Bogotá');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('VILLA ANDREA', '2', '4.62299407715996', '-74.1765262783587', 'Cl. 51c Sur #6, Bogotá');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('VILLA DE LA TORRE', '2', '4.62623139394955', '-74.1669657765739', 'CARRERA 80J · 42F - 34 SUR');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('MANDALAY', '2', '4.62202139851614', '-74.1431866648674', '0');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('SUPER MANZANA 8A CATEGORIA MENORES', '2', '4.62062103855552', '-74.1560348495225', 'CARRERA. 78J # 40B SUR 84');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('SUPER MANZANA 8A CATEGORIA JUVENIL', '2', '4.62062103855552', '-74.1560348495225', 'CARRERA. 78J # 40B SUR 84');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('TIMIZA STA CATALINA', '2', '4.61263086428549', '-74.1581700161851', 'CALLE 45 SUR CON 72U');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('ZARZAMORA', '2', '4.61943376908075', '-74.178389107195', 'CALLE 54C SUR · 81G BIS 54');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('RIVERAS DE OCCIDENTE JORNADA MAÑANA', '2', '4.64522364165935', '-74.1693264783586', 'CALLE 35 A SUR #93 10');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('PARQUE LA RIVERA', '2', '4.64842642114024', '-74.1780951071948', 'CALLE. 42a Sur #99C-19');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('PARQUE LA RIVIERA', '2', '4.6454890479682', '-74.177974480212', 'CALLE. 42f SUR #97C-14');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('PARROQUIA SANTA GUADALUPE', '2', '4.6391517628033', '-74.1731701495224', 'CARRERA. 90a Bis # 42A BIS S-31');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('PARQUE ALTAMAR', '2', '4.63560978896003', '-74.1721651783587', 'CARRERA. 88d BIS # 42C-55');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('PARQUE CONDADOS DE CASTILLA', '2', '4.63776106324693', '-74.1452081802119', 'CALLE. 7a Bis C #78h29');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('PARQUE PRINCIPAL DE TECHO', '2', '4.62625757914182', '-74.1472931206863', 'Cra. 78B #06 Sur-05, Kennedy, Bogotá');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('CARVAJAL OSORIO', '2', '4.60706497883082', '-74.1377969802123', 'TRANVERSAL 68h Bis A # 37C-30');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('FLORESTA SUR JORNADA TARDE', '2', '4.62119339267747', '-74.1279890206863', 'CALLE1 SUR # 68D');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('MARIA PAZ', '2', '4.63658860886056', '-74.1578179999999', 'CARRERA 82 # 2A 60 SUR');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('PARQUE LOS SOLDADITOS', '2', '4.64284464252732', '-74.1597657360311', 'CALLE 5 # 87G-40, KENNEDY, BOGOTÁ, D.C.');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('VILLA CLAUDIA', '2', '4.61793225713012', '-74.1289414711637', 'CARRERA 68F # 8 - 24');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('TINTAL NORTE', '2', '4.65093043327242', '-74.1598979258214', 'CARRERA 92CON CALLE 6B');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('JACKELINE', '2', '4.60990735313428', '-74.1649135443988', 'CALLE 47 B SUR # 77 U -50');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('CANCHA BOMBONERA', '2', '4.6209579444574', '-74.161777551376', 'CRA 79B # 41F 72');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('PARQUE LINEAL NUEVA CASTILLA MENORES', '2', '4.650265017153', '-74.1515040097846', 'Ak 88d #8C-21, Kennedy, Bogotá');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('SAN DIONISIO', '2', '4.63809007573031', '-74.1666554513759', 'CALLE 38C SUR 88-78');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('PARQUE UNIR 1 
JORNADA MAÑANA', '2', '4.64269801363913', '-74.1666898179337', 'CARRERA 89D # 1A -75SUR');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('SAN ANDRES 2DO SECTOR', '2', '4.6010254307994', '-74.1459224521122', 'Calle 43BS, Kennedy, Bogotá');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('PARQUE KENNEDY ORIENTAL SUPER 6', '2', '4.61781123965997', '-74.1530230648674', 'Cl. 39c Sur #73f-43, Bogotá');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('FLORESTA SUR JORNADA MAÑANA', '2', '4.62120408663536', '-74.1279997495225', 'CALLE1 SUR # 68D');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('PARQUE PARAISO CATEGORIA JUVENILES', '2', '4.64003197725223', '-74.169472255819', 'CALLE 40 # 89 D BIS');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('SALON COMUNAL ESTADOS UNIDOS', '2', '4.62513639764944', '-74.159123123276', 'CALLE 40A SUR #79-65, KENNEDY, BOGOTÁ');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('SALON COMUNAL ESTADOS UNIDOS', '2', '4.62513639764944', '-74.159123123276', 'CALLE 40A SUR #79-65, KENNEDY, BOGOTÁ');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('SALON COMUNAL ESTADOS UNIDOS', '2', '4.62513639764944', '-74.159123123276', 'CALLE 40A SUR #79-65, KENNEDY, BOGOTÁ');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('SALON COMUNAL ESTADOS UNIDOS', '2', '4.62513639764944', '-74.159123123276', 'CALLE 40A SUR #79-65, KENNEDY, BOGOTÁ');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('SALON COMUNAL ESTADOS UNIDOS', '2', '4.62513639764944', '-74.159123123276', 'CALLE 40A SUR #79-65, KENNEDY, BOGOTÁ');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('PARQUE ESTRUCTURANTE PATIO BONITO 1', '2', '4.64146118182224', '-74.1644138153447', 'AVENIDA EL TINTAL # 33 SUR 32');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('PARQUE ESTRUCTURANTE PATIO BONITO 2', '2', '4.64146118182224', '-74.1644138153447', 'AVENIDA EL TINTAL # 33 SUR 32');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('PARQUE ESTRUCTURANTE PATIO BONITO 3', '2', '4.64146118182224', '-74.1644138153447', 'AVENIDA EL TINTAL # 33 SUR 32');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('PARQUE ESTRUCTURANTE PATIO BONITO 4', '2', '4.64146118182224', '-74.1644138153447', 'AVENIDA EL TINTAL # 33 SUR 32');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('PARQUE ESTRUCTURANTE PATIO BONITO 5', '2', '4.64146118182224', '-74.1644138153447', 'AVENIDA EL TINTAL # 33 SUR 32');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('PARQUE ESTRUCTURANTE PATIO BONITO 6', '2', '4.64146118182224', '-74.1644138153447', 'AVENIDA EL TINTAL # 33 SUR 32');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('PARQUE ESTRUCTURANTE PATIO BONITO 7', '2', '4.64146118182224', '-74.1644138153447', 'AVENIDA EL TINTAL # 33 SUR 32');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('FLORALIA', '2', '4.6388150870509', '-74.1388155391227', 'TRANSVERSAL 68c # 30a Sur1');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('CAYETANO CAÑIZARES', '2', '4.62483849783301', '-74.1604255495226', 'Cra. 80 #40 55 Sur, Bogotá');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('GILMA JIMENEZ', '2', '4.62413413572559', '-74.17622004647', 'Cra. 87p #69 Sur-63, Bogotá');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('PARQUE SUPER MANZANA 6 ONLY', '2', '4.62177424414871', '-74.1498742918502', 'Cra. 78 #36A-12, Bogotá');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('PARQUE SAN IGNACIO PATINODROMO', '2', '4.65352509085314', '-74.1633708206862', 'Cl. 6a #94a-25, Kennedy, Bogotá');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('VISION COLOMBIA PARQUE LA PISTA JORNADA TARDE', '2', '4.65224856512787', '-74.1347598378844', 'Cl. 15 #79f-16, Bogotá');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('VISION COLOMBIA PARQUE LA PISTA JORNADA MAÑANA', '2', '4.65226995210329', '-74.1347598378844', 'Cl. 15 #79f-16, Bogotá');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('PARQUE BOITA MORABIA', '2', '4.60717017297157', '-74.1526906630141', 'Cl. 42b Sur # 72n');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('CANCHA BOMBONERA', '2', '4.6208937806854', '-74.1617024495226', 'CRA 79B # 41F 72');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('ARGELIA', '2', '4.61925225820805', '-74.1573982055601', 'CARRERA 72H CON CALLE 38 D SUR');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('ALCALDIA LOCAL', '2', '4.61930572814223', '-74.1573982055601', '04 Sur Transversal 78k 41 A, Bogotá');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('MARSELLA PARQUE', '2', '4.6362620950586', '-74.1291186341777', 'TRANSVERSAL 70 # 9A - 73');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('CONSENTIDOS 2

CARITAS ALEGRES', '2', '4.60610587330877', '-74.144404551376', 'CARRERA 72F BIS A # 39 F 20 SUR

CARRERA 72F - 38B 78 SUR');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('POLI FUTBOL PARQUE LA ALEJANDRA', '2', '4.60587329605723', '-74.1482399711638', 'Cra. 72 I # a, Bogotá');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('ALCALDIA LOCAL
POLI AJEDREZ', '2', '4.61926829918873', '-74.1573713834696', '04 Sur Transversal 78k 41 A, Bogotá');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('LICEO PEÑEROS CORTES
AJEDREZ', '2', '4.62512500056472', '-74.1434434306895', 'Cl. 2 Bis #73c55, Bogotá');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('CLASS ROMA POLIMOTOR AJEDREZ', '2', '4.61955056904364', '-74.1290486532293', 'KR 68 F 3 42 SUR

KR 68 D 2 69 SUR');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('JARDIN COMUNITARIO ILUSIONES Y FANTASIAS', '2', '4.60329549150694', '-74.141423907195', 'CARRERA 68I 39F 06 SUR');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('LA IGUALDAD

LAS OVEJITAS

PILITOS', '2', '4.62457357388196', '-74.1280635537558', 'CALLE 2 B 68 D 12

Calle 2 B # 68F -27');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('CONTRAUNIDOS POLI FUTSAL', '2', '4.64078724961206', '-74.1595249495224', 'CALLE. 2 # 87-15 SUR,');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('PARQUE ALTAMAR
POLI FUTSAL', '2', '4.63540298901343', '-74.1721595783586', 'CARRERA. 88d BIS # 42C-55');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('FLORALIA', '2', '4.607949259460351', '-74.1368514441809', 'CALLE 37 BIS No. 68 H 79 S.');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('CIUDAD TINTAL', '2', '4.65116173635152', '-74.1616369287837', 'Cll 6 a # 92 - 20 CASA 39 PRADOS');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('NUEVA CASTILLA', '2', '4.64971877651725', '-74.1517717844453', 'CLL 8 a # 88 -90 Interior 3 APT 109 TORRE 2');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('LAS VEGAS 2 SECTOR', '2', '4.63687068863435', '-74.1709299378844', 'CRA 88g # 42F71 sur');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('MARIA PAZ 1', '2', '4.63608658257265', '-74.1572980188329', 'CALLE 5 B # 81 D 12 SUR');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('LUCERNA', '2', '4.61385477678015', '-74.1458239206865', '
CALLE 38 A #72M12 SUR
');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('LA IGUALDAD 
MI BELLA AVENTURA', '2', '4.62252840445288', '-74.1294666513759', 'KR 69 A 1 37');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('TINTAL1
TINTAL2', '2', '4.6560361362135', '-74.1591868802119', 'CLL7 # 94-78 CASA 237
Calle 7 # 94 -79
');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('CARIMAGUA 1ER SECTOR', '2', '4.61139007752489', '-74.145115751376', 'CALLE 38 C sur 72 J 45');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('MARIA PAZ 2', '2', '4.63709522124577', '-74.1553850846552', 'CARRERA 81 C # 2 B 36');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('MI BELLA INCANCIA

CHIQUILINES', '2', '4.67279585885246', '-74.0943053802118', 'CARRERA 68H # 39-14 SUR

TRANNSV 68J BIS 39B 25 SUR');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('SAN CARLOS', '2', '4.63312809582042', '-74.1545962495225', 'Carrera 80 b 2 74 ,Kennedy, Bogotá');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('BOITA', '2', '4.60737207442762', '-74.1556013248561', 'CALLE 48B SUR # 72K - 13');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('CONJUNTO RESIDENCIAL CARIMAGUA ETAPA 3', '2', '4.61400698056325', '-74.1483088369853', 'CALLE 39 SUR # 72N 42');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('VEGAS DE SANTA ANA', '2', '4.61785128531558', '-74.1812350272541', 'Cra. 81j #57A-62, Bosa, Bogotá');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('DELICIAS TAEKWONDO ADAPTADO', '2', '4.59976132105085', '-74.1464969783589', 'CARRERA 72B # 44C 19 SUR SEDE B');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('CAYETANO CAÑIZARES', '2', '4.62494543685443', '-74.1604148206864', 'Cra. 80 #40 55 Sur, Bogotá');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('SALON COMUNAL LUCERNA', '2', '4.61295587113724', '-74.1463163648674', 'Cra. 72m #38c Sur3, Bogotá');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('BRITALIA JAC', '2', '4.62220879847069', '-74.1708391783588', 'Cra. 81b #47A-16Sur, Kennedy, Bogotá');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('AMERICAS 68 SEGUNDA DIVISION', '2', '4.62391330172985', '-74.1253228920687', 'AVENIDA 68 # 1-63');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('PARQUE TINTAL FASE 3', '2', '4.65089479149491', '-74.1680996648672', 'CALLE 2 # 93D -66');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('JAC LAS MARAGARITAS', '2', '4.63502372187213', '-74.1775140248294', 'calle 48 sur 89 b 43');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('TABAKU', '2', '4.64012433165184', '-74.1543371312073', 'CARRERA 82A # 6 - 71');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('COLISEO CASTILLA', '2', '4.63947452682236', '-74.1391972423276', 'a 73-87,, Cl. 8b Bis #7343, Bogotá');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('COLISEO CAYETANO CAÑIZARES', '2', '4.624881273443511', '-74.1605328378845', 'Cra. 80 #40 55 Sur, Bogotá');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('DELICIAS - SAN ANDRES 1 SECTOR', '2', '4.5978393183296', '-74.1425744017033', 'CALLE 43F SUR 68F KENNEDY BOGOTA');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('PERPETUO SOCCORRO', '2', '4.61097688353462', '-74.1663544783588', 'CARRERA 78 No. 49-43');
INSERT INTO escuelas_staging (nombre, tipo, latitud, longitud, direccion) VALUES ('', NULL, NULL, NULL, NULL);

COMMIT;
