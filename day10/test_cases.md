
ID	Описание	Входные данные (ключевые)	Ожидание
TC1	Сумма = 0	total_amount=0	valid=False, reason=сумма
TC2	Сумма = 1_000_000	total_amount=1_000_000	valid=False
TC3	Сумма = 999_999.99	...	valid=True
TC4	Новый пользователь, сумма=15000	created_at=8 дней, total=15000	valid=True
TC5	Новый пользователь, сумма=15001	...	valid=False
TC6	51 позиция	items=51	valid=False
TC7	Alcohol, age_verified=False	...	valid=False
TC8	Alcohol, время 07:59	...	valid=False
TC9	Alcohol, время 23:01	...	valid=False
TC10	Alcohol, время 08:00	...	valid=True
TC11	Сумма 100001	risk_score=0.9	
TC12	Сумма 100000	risk_score=0.0 (или др.)	
TC13	email changed 59 мин назад	risk_score += 0.2	
TC14	email changed 61 мин назад	risk_score без изменений	
TC15	Страны не совпадают	risk_score += 0.3	
TC16	Страны не совпадают + сумма>100k	risk_score = min(1.0, 0.9+0.3)=1.0	
TC17	Все правила сразу	valid=False (сумма > 1M)	
TC18	Все правила ок	valid=True, risk=0.0	
TC19	Alcohol + новый пользователь	проверка комбинации	
TC20	Граница времени 08:00:00	valid=True	
TC21	Граница времени 23:00:00	valid=True	
TC22	Граница времени 07:59:59	valid=False	
TC23	Граница времени 23:00:01	valid=False	
TC24	Сумма 0.01	valid=True	
TC25	Сумма 999999.99	valid=True	
TC26	Позиций 50	valid=True	
TC27	Позиций 51	valid=False	
TC28	Новый пользователь ровно 7 дней	valid=True (если >7)	
TC29	Новый пользователь 6.9 дней	valid=False	
TC30	Все риски сразу	risk_score=1.0	
TC31	Нет рисков	risk_score=0.0	
TC32	Дубликат заказа (не проверяем)	тест на устойчивость