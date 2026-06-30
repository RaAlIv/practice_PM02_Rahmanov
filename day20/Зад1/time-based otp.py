# Исправленный список сотрудников (список словарей)
employers = [
    {'emp_id': '101', 'name': 'Иван', 'on_vacation': False},
    {'emp_id': '102', 'name': 'Иван', 'on_vacation': True},
    {'emp_id': '103', 'name': 'Иван', 'on_vacation': False}
]

turnstile = {'turnstile_id': '1'}

def turnstile_access(emp_id, turnstile_id):
    employee = None
    for emp in employers:
        if emp['emp_id'] == str(emp_id): 
            employee = emp
            break
    
    if employee is None:
        print('no accept, user out of database')
        return False
    
    if employee['on_vacation']:
        print(f'no accept {employee["name"]} on vacation')
        return False
    
    open_turn()
    return True

def open_turn():
    print('accept access')
    return True

turnstile_access(102, 1)  
turnstile_access(101, 1)  