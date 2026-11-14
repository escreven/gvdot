--
-- An SQLite schema definition for the registration.ipynb example notebook.
--

pragma foreign_keys = on;

begin transaction;

drop table if exists registration;
drop table if exists meeting;
drop table if exists section;
drop table if exists assistant;
drop table if exists class;
drop table if exists course;
drop table if exists term;
drop table if exists student;
drop table if exists instructor;

create table instructor (
    id    integer not null primary key,
    name  text    not null,
    email text    not null unique
);

create table student (
    id    integer not null primary key,
    name  text    not null,
    email text    not null unique,
    level text    not null,
    check (level in ('undergraduate', 'graduate'))
);

create table term (
    id         integer not null primary key,
    name       text    not null unique,
    start_date text    not null,
    end_date   text    not null,
    check (start_date <= end_date)
);

create table course (
    id    integer not null primary key,
    code  text    not null unique,
    title text    not null
);

create table class (
    id            integer not null primary key,
    course_id     integer not null references course (id),
    term_id       integer not null references term (id),
    instructor_id integer not null references instructor (id)
);

create table assistant (
    class_id integer not null references class (id),
    student_id  integer not null references student (id),
    primary key (class_id, student_id)
);

create table section (
    class_id integer not null references class (id),
    section_id  integer not null,
    lead_ta_id  integer,
    primary key (class_id, section_id),
    foreign key (class_id, lead_ta_id)
        references assistant (class_id, student_id)
);

create table meeting (
    class_id    integer not null,
    meeting_id  integer not null,
    day_of_week integer not null,
    start_time  text not null,
    end_time    text not null,
    section_id  integer,
    location    text not null,
    kind        text not null,
    primary key (class_id, meeting_id, day_of_week, start_time),
    foreign key (class_id) references class (id),
    foreign key (class_id, section_id)
        references section (class_id, section_id),
    check (day_of_week between 1 and 7),
    check (start_time < end_time),
    check (end_time glob '[0-2][0-9]:[0-5][0-9]' and end_time < '24:00'),
    check (start_time glob '[0-2][0-9]:[0-5][0-9]' and start_time < '24:00'),
    check (kind in ('lecture', 'discussion'))
    check (kind = 'lecture' and section_id is null or
           kind = 'discussion' and section_id is not null)
);

create table registration (
    student_id integer not null references student (id),
    class_id integer not null,
    section_id integer not null,
    status text not null default 'pending'
        check (status in ('pending', 'approved', 'waitlist')),
    waitlist_priority integer,
    primary key (student_id, class_id, section_id),
    foreign key (class_id, section_id)
        references section (class_id, section_id),
    check (status = 'waitlist' and waitlist_priority is not null
           and waitlist_priority > 0 or
           status <> 'waitlist' and waitlist_priority is null)
);

commit;
