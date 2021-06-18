drop table if exists view;

create table if not exists view (
	id serial primary key,
	xid varchar(32) not null,
	name varchar(32) not null,
	configuration text not null
);
