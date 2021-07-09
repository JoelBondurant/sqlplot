drop table if exists "team" cascade;

create table if not exists "team" (
	xid char(32) primary key,
	name varchar(32) not null,
	created timestamp not null default current_timestamp,
	updated timestamp not null default current_timestamp
);
