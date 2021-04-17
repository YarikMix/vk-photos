from pytrovich.enums import NamePart, Gender, Case
from pytrovich.maker import PetrovichDeclinationMaker


maker = PetrovichDeclinationMaker()

def decline(first_name, last_name, sex):
    """Возвращает имя и фамилию в родительном падаже."""
    if sex == 1:
        first_name = maker.make(NamePart.FIRSTNAME, Gender.FEMALE, Case.GENITIVE, first_name)
        last_name = maker.make(NamePart.LASTNAME, Gender.FEMALE, Case.GENITIVE, last_name)
    elif sex == 2:
        first_name = maker.make(NamePart.FIRSTNAME, Gender.MALE, Case.GENITIVE, first_name)
        last_name = maker.make(NamePart.LASTNAME, Gender.MALE, Case.GENITIVE, last_name)
    return f"{first_name} {last_name}"