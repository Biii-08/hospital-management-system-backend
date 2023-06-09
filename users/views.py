from .models import CustomUser, PatientProfile, DoctorProfile, Review, DoctorAvailability, TimeSlot, Department, Appointment
from .serializers import PatientProfileSerializer, DoctorProfileSerializer, ReviewSerializer, DoctorAvailabilitySerializer, DepartmentSerializer, AppointmentSerializer
from rest_framework import viewsets
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.decorators import action
from .serializers import UserSerializer
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework import status
from datetime import datetime
from rest_framework import generics
from .serializers import TimeSlotSerializer


class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # Add custom claims here.
        token['name'] = user.name
        token['is_patient'] = user.is_patient
        return token


class UserViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """
    queryset = CustomUser.objects.all()
    serializer_class = UserSerializer
    permission_classes = []


class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer


class RegisterView(APIView):
    def post(self, request):
        serializer = UserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class PatientProfileViewSet(viewsets.ModelViewSet):
    queryset = PatientProfile.objects.all()
    serializer_class = PatientProfileSerializer

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(
            instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save(is_complete=True)
        return Response(serializer.data)


class DoctorProfileViewSet(viewsets.ModelViewSet):
    queryset = DoctorProfile.objects.all()
    serializer_class = DoctorProfileSerializer

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(
            instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save(is_complete=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def get_doctors_by_department(self, request):
        department_id = request.query_params.get('department_id')
        try:
            department = Department.objects.get(id=department_id)
            doctors = DoctorProfile.objects.filter(department=department)
            serializer = self.serializer_class(
                doctors, many=True, context={'request': request})
            return Response(serializer.data)
        except Department.DoesNotExist:
            return Response({'detail': f'Department with id {department_id} does not exist.'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['post'])
    def set_availability(self, request, pk=None):
        try:
            doctor = DoctorProfile.objects.get(pk=pk)
        except DoctorProfile.DoesNotExist:
            return Response({'detail': f'Doctor with id {pk} does not exist.'}, status=status.HTTP_404_NOT_FOUND)

        data = request.data
        try:
            data = data['data']
        except:
            data = data

        for day_data in data:
            day = day_data.get('day')
            time_slots_data = day_data.get('timeSlots')
            if day and time_slots_data:
                day_index = next(
                    (index for (index, d) in DoctorAvailability.WEEKDAYS if d == day), None)
                if day_index is not None:
                    time_slots = []
                    for time_slot_data in time_slots_data:
                        start_time = time_slot_data.get('startTime')
                        end_time = time_slot_data.get('endTime')
                        online_appointment_price = time_slot_data.get(
                            'online_appointment_charge')
                        physical_appointment_price = time_slot_data.get(
                            'physical_appointment_charge')
                        if start_time and end_time:
                            time_slot = TimeSlot.objects.create(
                                start_time=start_time,
                                end_time=end_time,
                                online_appointment_charge=online_appointment_price,
                                physical_appointment_charge=physical_appointment_price
                            )
                            time_slots.append(time_slot)
                    availability, _ = DoctorAvailability.objects.get_or_create(
                        doctor=doctor,
                        day=day_index
                    )
                    availability.time_slots.set(time_slots)
                    availability.save()

        return Response({'detail': 'Availability set successfully.'})

    @action(detail=True, methods=['get'])
    def get_availability(self, request, pk=None):
        doctor = self.get_object()
        availability = doctor.availability.all()
        serializer = DoctorAvailabilitySerializer(
            availability, many=True, context={'request': request})
        return Response(serializer.data)


class DoctorAvailabilityViewSet(viewsets.ModelViewSet):
    queryset = DoctorAvailability.objects.all()
    serializer_class = DoctorAvailabilitySerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Ensure that the specified doctor in the availability object is the same as the authenticated user.
        if serializer.validated_data['doctor'].user != request.user:
            return Response({'error': 'Invalid doctor profile.'}, status=status.HTTP_400_BAD_REQUEST)

        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class ReviewViewSet(viewsets.ModelViewSet):
    queryset = Review.objects.all()
    serializer_class = ReviewSerializer


class ActivateAccountView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, token):
        try:
            payload = RefreshToken(token).payload
            user_id = payload['user_id']
            user = CustomUser.objects.get(id=user_id)
            print(user.id)
            if not user.is_active:
                user.is_active = True
                user.save()
                print(user.is_active)
                return Response({'message': 'Account activated successfully'}, status=status.HTTP_200_OK)
            else:
                return Response({'message': 'Account already activated'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class DepartmentViewset(viewsets.ModelViewSet):
    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer


class AppointmentViewSet(viewsets.ModelViewSet):
    queryset = Appointment.objects.all()
    serializer_class = AppointmentSerializer

    # def get_queryset(self):
    #     user = self.request.user
    #     if user.is_authenticated:
    #         return Appointment.objects.filter(user=user)
    #     return Appointment.objects.none()

    @action(detail=False, methods=['get'])
    def get_appointments_by_doctor(self, request):
        doctor_id = request.query_params.get('doctor_id')
        print(doctor_id)

        try:
            doctor = DoctorProfile.objects.get(id=doctor_id)
            apointments = Appointment.objects.filter(doctor=doctor.id)
            print(apointments)
            serializer = self.serializer_class(
                apointments, many=True, context={'request': request})
            return Response(serializer.data)
        except DoctorProfile.DoesNotExist:
            return Response({'detail': f'Doctor with id {doctor_id} does not exist.'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['get'])
    def get_appointments_by_patient(self, request):
        patient_id = request.query_params.get('patient_id')
        print(patient_id)

        try:
            patient = PatientProfile.objects.get(id=patient_id)
            apointments = Appointment.objects.filter(patient=patient.id)
            serializer = self.serializer_class(
                apointments, many=True, context={'request': request})
            return Response(serializer.data)
        except DoctorProfile.DoesNotExist:
            return Response({'detail': f'Patient with id {patient_id} does not exist.'}, status=status.HTTP_404_NOT_FOUND)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # Extract validated data
        validated_data = serializer.validated_data

        # Get or create PatientProfile and DoctorProfile objects
        patient_profile = validated_data.pop('patient')
        doctor_profile = validated_data.pop('doctor')

        # Get TimeSlot object
        time_slot = validated_data.pop('time_slot')
        instance = TimeSlot.objects.create(start_time=time_slot['start_time'],end_time=time_slot['end_time'],online_appointment_charge=time_slot['online_appointment_charge'],physical_appointment_charge=time_slot['physical_appointment_charge'])
        # Create Appointment object
        appointment = Appointment.objects.create(
            patient=patient_profile,
            doctor=doctor_profile,
            time_slot=instance,
            **validated_data
        )

        # Serialize and return Appointment object
        serializer = self.get_serializer(appointment)
        return Response(serializer.data, status=status.HTTP_201_CREATED)