try:
    from App import database
    from App.logs import logger
except:
    import database
    #from logs import logger
    
import random, itertools

class Place:
    def __init__(self, column_index, row_index, place_number):
        self.column_index = column_index
        self.row_index = row_index
        self.place_number = place_number

    def infos(self):
        return [self.column_index, self.row_index, self.place_number]


class InnerIterator:
    def __init__(self, grade_names: list):
        self.grade_names = grade_names
        self.current_index = 0

    def __iter__(self):
        return self

    def __next__(self):
        if self.current_index == len(self.grade_names) - 1:
            self.current_index = -1

        self.current_index += 1
        return self.grade_names[self.current_index]


class OuterIterator:
    def __init__(self, exam_names: list, grade_names_iterators: list[InnerIterator]):
        self.exam_names = exam_names
        self.grade_names_iterators = grade_names_iterators
        self.current_index = 0

    def __iter__(self):
        return self

    def __next__(self):
        if self.current_index == len(self.exam_names) - 1:
            self.current_index = -1

        self.current_index += 1
        return (self.exam_names[self.current_index], self.grade_names_iterators[self.current_index])

    def __prev__(self):
        if self.current_index == 0:
            self.current_index = len(self.exam_names)
            
        self.current_index -= 1
        return (self.exam_names[self.current_index], self.grade_names_iterators[self.current_index])
        

def get_key_with_max_value(dictionary):
    if not dictionary:
        return None
    return max(dictionary, key=dictionary.get)

def get_iterator(exams: dict) -> OuterIterator:
    grade_names_iterators = []
    for exam_name, grade_names in exams.items():
        random.shuffle(grade_names)
        grade_names_iterators.append(InnerIterator(grade_names=grade_names))

    return OuterIterator(list(exams.keys()), grade_names_iterators)    
    
def distribute_students(exams: dict, classroomsToUse: list, all_grades: dict[str: list], rules: dict):
    classrooms_backup = database.get_name_given_classrooms(classroomsToUse)
    iterator = get_iterator(exams)

    class_counts = {grade: len(students) for grade, students in all_grades.items()}
    placed_count = 0
    un_placed_count = 0
    
    outer_attempts = 5
    while outer_attempts and is_there_any_student_left(class_counts):
        classrooms = classrooms_backup.copy()
        
        # Salonlar üzerinde gezinme
        for classroom_name in classrooms_backup:
            print(f"--------------------{classroom_name}--------------------")
            random_index = random.randint(0, len(exams) - 1)
            iterator.current_index = random_index
            
            classroom = classrooms.get(classroom_name)
            arrangement = classroom.get("oturma_duzeni")

            # Salonun öğretmen masasına yerleştirme
            if (rules.get("OgretmenMasasinaOgretmenOturabilir")) and (classrooms.get(classroom_name).get("ogretmen_masasi") is None):
                the_most_crowded_grade_name = get_key_with_max_value(class_counts)
                if class_counts.get(the_most_crowded_grade_name):
                    student = all_grades.get(the_most_crowded_grade_name)[0]
                    classrooms[classroom_name]["ogretmen_masasi"] = student
                    
            # Salonun masalarına yerleştirme
            for column_index, column in enumerate(arrangement):
                for row_index, desk in enumerate(column):
                    for place_number, current_place in desk.items():
                        place_object = Place(column_index=column_index, row_index=row_index, place_number=place_number)
                        
                        attempts = len(exams)
                        placed = False
                        while attempts and not placed:
                            # Her denemede yeni bir sınav ve o sınava dahil sınıf seç
                            exam_name, grade_names_iterator = iterator.__next__()
                            grade_name = grade_names_iterator.__next__()
                            
                            for _ in range(len(exams.get(exam_name))):
                                if all_grades.get(grade_name):
                                    break
                                else:
                                    grade_name = grade_names_iterator.__next__()
                            else:
                                # Bu sınava girecek hiç öğrenci kalmamış 
                                attempts = 0
                                continue
                            
                            # Seçilen sınava dahil sınıftan bir öğrenci seç
                            student = all_grades.get(grade_name)[0]
                            print(student)
                            current_gender = student[3]
                            place_suitable = is_place_suitable(classroom=classroom, arrangement=arrangement, place=current_place, place_object=place_object, place_index=list(desk.keys()).index(place_number), current_exam_name=exam_name, student=student, current_gender=current_gender, rules=rules)

                            # Yer uygun ise öğrenciyi oraya yerleştir
                            if place_suitable:
                                classrooms[classroom_name]["oturma_duzeni"][column_index][row_index][place_number] = {"exam_name": exam_name, "student": student}
                                all_grades[grade_name].remove(student)
                                random.shuffle(all_grades[grade_name])
                                class_counts[grade_name] -= 1
                                placed = True
                                placed_count += 1
                                print(f"Placed: {desk}")
                            
                            # Eğer sorun cinsiyet ise farklı cinsiyetten bir öğrenci seç
                            elif place_suitable == -1:
                                for index, student in enumerate(all_grades.get(grade_name)):
                                    if ((not index) and (current_gender != student[3])): 
                                        student = all_grades.get(grade_name)[0]
                                        print(student)
                                        place_suitable = is_place_suitable(classroom=classroom, arrangement=arrangement, place=current_place, place_object=place_object, place_index=list(desk.keys()).index(place_number), current_exam_name=exam_name, student=student, current_gender=current_gender, rules=rules)
                                        if place_suitable:
                                            classrooms[classroom_name]["oturma_duzeni"][column_index][row_index][place_number] = {"exam_name": exam_name, "student": student}
                                            all_grades[grade_name].remove(student)
                                            random.shuffle(all_grades[grade_name])
                                            class_counts[grade_name] -= 1
                                            placed = True
                                            placed_count += 1
                                            print(f"Placed: {desk}")
                                        
                            else:
                                attempts -= 1
                                print(f"Not placed: {desk}")
                            print()
        outer_attempts -= 1
                            
    if is_there_any_student_left(class_counts):
        return {"Classrooms": classrooms_backup, "Status": False, "Class-Counts": class_counts, "Placed-Count": placed_count, "Un-Placed-Count": un_placed_count   }
    return {"Classrooms": classrooms_backup, "Status": True, "Class-Counts": class_counts, "Placed-Count": placed_count, "Un-Placed-Count": un_placed_count}


def get_places(oturma_duzeni: list) -> list[Place]:
    places = []
    for column_index, column in enumerate(oturma_duzeni):
        for desk_index, desk in enumerate(column):
            for place_index, desk_no in enumerate(desk):
                places.append(Place(column_index, desk_index, place_index))

    return places

def is_place_suitable(classroom: dict, arrangement: list, place: None or tuple, place_object: Place, place_index: int, current_exam_name: str, student: tuple, current_gender: str, rules: dict):
    """_summary_
    Args:
        classroom (dict): Current classroom -> 
        {
            "derslik_adi": str,
            "ogretmen_yonu": "Solda" or "Sağda",
            "kacli": "1'li" or "2'li",
            "oturma_duzeni": list[list]
        }
        arrangement (list): The list that contains all the column objects
        place (none or tuple): Current place
        place_object (Place): Place object which has current place's informations
        place_index (int): Index of place in the current desk
        exam (str): The exam of student
        student (tuple): [] or (0: number, 1: name, 2: surname, 3: gender, 4:grade)
        current_gender (str): Gender of student. Index 3.
        rules (dict): {
                        "SideBySideSitting" -> Ayni sinava giren ogrenciler yan yana oturabilir,
                        "BackToBackSitting" -> “““ ogrenciler arka arkaya oturabilir,
                        "CrossByCrossSitting" -> “““ grenciler capraz oturabilir,
                        "KizErkekYanYanaOturabilir" -> Kız erkek yan yana oturabilir,
                        "OgretmenMasasineOgrenciOturabilir" -> Ogrenciler ogretmen masasina oturabilir.
                    }

    Returns:
        bool: Ogrenci oturabilir ise True, oturamaz ise False dondurur
    """
    
    # Check if the desk is empty
    if place.get("student") is not None:
        return False
    
    kacli_salon = classroom.get("kacli")
    column_index, row_index, place_number = place_object.infos()
    print(f"Place: {place}, Column index: {column_index}, Row index: {row_index}, Place index: {place_index}")
    
    if not rules.get("CrossByCrossSitting"):
        if kacli_salon == "1'li":
            # En solda ve en önde değil isen sol önünü kotrol et
            # If your not at the very front or at the very left column and you have a front desk and you are sitting in the right place in your desk so you have left front place, check it 
            if not ((row_index == 0) or ((column_index == 0) and not (place_index))):
                try:
                    left_fore_place = list(arrangement[column_index - 1][row_index - 1].values())[0]
                # Your left column has no desk at this row
                except IndexError:
                    return True

                if (not isinstance(left_place, dict)) or (left_place.get("exam_name") == current_exam_name):
                    return False
                
            try:
                left_back_place = list(arrangement[column_index - 1][row_index + 1].values())[0]
            # Your left colum has no desk at next row
            except IndexError:
                return True
            
            if (not isinstance(left_back_place, dict)) or (left_back_place.get("exam_name") == current_exam_name):
                    return False

        if kacli_salon == "2'li":
            # En solda ve sol yerde değilsen sol önünü kotrol et
            if not ((row_index == 0) or ((column_index == 0) and not (place_index))):
                if not place_index:
                    try:
                        left_fore_place = list(arrangement[column_index - 1][row_index - 1].values())[0]
                    # Your left column has no desk at this row
                    except IndexError:
                        return True
                    
                    if (not isinstance(left_fore_place, dict)) or (left_fore_place.get("exam_name") == current_exam_name):
                        return False
                elif place_index:
                    left_fore_place = list(arrangement[column_index][row_index - 1].values())[0]
                    if (not isinstance(left_fore_place, dict)) or (left_fore_place.get("exam_name") == current_exam_name):
                        return False
            
            try:
                left_back_place = list(arrangement[column_index - 1][row_index + 1].values())[0]
            # Your left colum has no desk at next row
            except IndexError:
                return True
            
            if (not isinstance(left_back_place, dict)) or (left_back_place.get("exam_name") == current_exam_name):
                return False
                   
    if not rules.get("BackToBackSitting"):
        # 1'li ve 2'li de aynı kurallar geçerli olduğu için burada koşulu dışarı alıyoruz
        if row_index != 0:
            # Burada da sadece oturma yönüne göre karşılaştırılacak öğrenciyi seçiyoruz
            if not place_index:
                fore_student = list(arrangement[column_index][row_index - 1].values())[0]

            elif place_index:
                fore_student = list(arrangement[column_index][row_index - 1].values())[1]

            if (not isinstance(left_back_place, dict)) or (left_back_place.get("exam_name") == current_exam_name):
                return False
    
    if not rules.get("SideBySideSitting"):
        if kacli_salon == "1'li":
            # En solda değilsen solunu kontrol et
            # If you are not on the very left column, check the place on your left column because the desks contain only one place
            if column_index != 0:
                try:
                    left_place = list(arrangement[column_index - 1][row_index].values())[0]
                # Your left column has no desk at this row
                except IndexError:
                    return True
                
                if (not isinstance(left_place, dict)) or (left_place.get("exam_name") == current_exam_name):
                    return False
                
        if kacli_salon == "2'li":
            # En solda ve sol yerde değilsen solunu kontrol et
            # If you are not the most left column and at its left sided place, check your left column.
            if not ((column_index == 0) and (not place_index)):
                # Check the right placed place in the left column if your place index is 0 in your current desk
                if not place_index:
                    try:
                        left_place = list(arrangement[column_index - 1][row_index].values())[1]
                    # Your left column has no desk at this row
                    except IndexError:
                        return True
                        
                    if (not isinstance(left_place, dict)) or (left_place.get("exam_name") == current_exam_name):
                        return False
                        
                # Check your left in the same desk if your place index is 1 in your current desk
                elif place_index:
                    left_place = list(arrangement[column_index][row_index].values())[0]
                    if (not isinstance(left_place, dict)) or (left_place.get("exam_name") == current_exam_name):
                        return False
                    
        # Cinsiyet kontrolü buraya koyuldu çünkü aynı yeri kontrol edecek
        # Gender check is here because both them will check same place        
        if not rules.get("KizErkekYanYanaOturabilir"):
            if (left_place.get("student")[3] == student[3]):
                return -1    

    return True

def is_there_any_student_left(classroomCounts: dict):
    counts = [count for gradeName, count in classroomCounts.items()]
    if any(counts):
        return True
    return False

def print_classrooms(classrooms: dict or tuple):
    for classroomName, classroom in classrooms.items():
        print(f"{classroomName}:")
        print(f"\tOgretmen masasi:", classroom["ogretmen_masasi"], "\n")
        columns = classroom["oturma_duzeni"]
        for column in columns:
            for desk in column:
                print(f"\t{desk}")
            print("\t---")
        print()

def distribute(exam):
    exams = exam.exams
    classroomsToUse = exam.classroomNames
    all_grades = database.get_grade_given_students(exams)

    # Öğrencilerin sırasını karıştır
    for grade_name in all_grades:
        random.shuffle(all_grades.get(grade_name))
        
    rules = exam.rules
    print("-------------------\t\tSTARTING\t\t-----------------")
    result = distribute_students(exams, classroomsToUse, all_grades, rules)
    print("-------------------\t\tENDED\t\t-----------------")

    return result


if __name__ == '__main__':
    from Frames.create_exam_frame import Exam
    exams = {
        "Sınav1": {"gradeNames": ["9/A", "9/B", "9/C", "9/D"]},
        "Sınav2": {"gradeNames": ["10/A", "10/B", "10/C", "10/D"]},
        "Sınav3": {"gradeNames": ["11/A", "11/B", "11/C", "11/D"]},
        "Sınav4": {"gradeNames": ["12/A", "12/B", "12/C", "12/D"]},
    }
    
    classroomNames = ["9/A", "9/B", "9/C", "9/D", "10/A", "10/B", "10/C", "10/D", "11/A", "11/B", "11/C", "11/D", "12/A", "12/B", "12/C", "12/D"]
    
    rules = {
        "BackToBackSitting": 0,
        "SideBySideSitting": 0,
        "CrossByCrossSitting": 0,
        "KizErkekYanYanaOturabilir": 0,
        "OgretmenMasasinaOgretmenOturabilir": 1
    }
    
    exam = Exam(exams, classroomNames, rules)
    result = distribute(exam)
    print_classrooms(result.get("Classrooms"))
    print(f"Status: {result.get('Status')}")
    print(f"Class-Counts: {result.get('Class-Counts')}")
    print(f"Placed-Count: {result.get('Placed-Count')}")
    print(f"Unplaced-Count: {result.get('Un-Placed-Count')}")