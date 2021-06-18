drop table if exists dashboard;

create table if not exists dashboard (
	id serial primary key,
	xid varchar(32) not null,
	name varchar(32) not null,
	configuration text not null
);
