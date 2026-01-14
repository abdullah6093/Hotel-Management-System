INSERT INTO Customer (name, phone, email, address)
VALUES
('Ali Khan', '0300-1111111', 'ali@example.com', 'Lahore, Pakistan'),
('Sara Ahmed', '0301-2222222', 'sara@example.com', 'Karachi, Pakistan'),
('John Doe', '0302-3333333', 'john@example.com', 'Islamabad, Pakistan');

INSERT INTO RoomType (type_name, description, base_price_per_night)
VALUES
('Single', 'Single bed, basic amenities', 5000.00),
('Double', 'Double bed, suitable for two guests', 8000.00),
('Deluxe', 'Luxury room with premium features', 12000.00);

INSERT INTO Room (room_number, room_type_id, room_image, status)
VALUES
('101', 1, 'img/room101.jpg', 'Available'),
('102', 1, 'img/room102.jpg', 'Booked'),
('201', 2, 'img/room201.jpg', 'Available'),
('202', 2, 'img/room202.jpg', 'Maintenance'),
('301', 3, 'img/room301.jpg', 'Available');

INSERT INTO Booking (customer_id, room_id, check_in_date, check_out_date, booking_status, total_amount)
VALUES
(1, 2, '2025-01-10', '2025-01-12', 'Confirmed', 10000.00),
(2, 3, '2025-02-01', '2025-02-05', 'Pending', 32000.00),
(3, 5, '2025-03-15', '2025-03-18', 'Cancelled', 0.00);

INSERT INTO Payment (booking_id, amount_paid, payment_method, payment_status)
VALUES
(1, 10000.00, 'Card', 'Paid'),
(2, 0.00, 'Online', 'Pending'),
(3, 0.00, 'Cash', 'Refunded');

INSERT INTO Employee (name, role, phone, email)
VALUES
('Asad Mehmood', 'Receptionist', '0305-4444444', 'asad@example.com'),
('Fatima Noor', 'Housekeeping', '0306-5555555', 'fatima@example.com'),
('Bilal Hussain', 'Manager', '0307-6666666', 'bilal@example.com');

INSERT INTO Shift (shift_name, start_time, end_time)
VALUES
('Morning', '08:00:00', '16:00:00'),
('Evening', '16:00:00', '00:00:00'),
('Night', '00:00:00', '08:00:00');


INSERT INTO EmployeeShift (employee_id, shift_id, shift_date)
VALUES
(1, 1, '2025-01-10'),
(2, 2, '2025-01-10'),
(3, 3, '2025-01-10');

INSERT INTO MenuItem (item_name, item_price, category, item_image)
VALUES
('Chicken Biryani', 500.00, 'Food', 'img/biryani.jpg'),
('Tea', 100.00, 'Beverage', 'img/tea.jpg'),
('Club Sandwich', 350.00, 'Food', 'img/sandwich.jpg');

INSERT INTO RoomServiceOrder (booking_id)
VALUES
(1),
(2);

INSERT INTO RoomServiceOrderItem (order_id, item_id, quantity, subtotal)
VALUES
(1, 1, 2, 1000.00),  
(1, 2, 3, 300.00),   
(2, 3, 1, 350.00);   
