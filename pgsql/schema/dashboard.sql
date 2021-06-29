drop table if exists dashboard;

create table if not exists dashboard (
	id serial primary key,
	xid char(32) not null,
	user_xid char(32) not null,
	name varchar(32) not null,
	configuration text not null,
	created timestamp not null default current_timestamp,
	updated timestamp not null default current_timestamp
);
