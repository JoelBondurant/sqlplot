drop table if exists "user";

create table if not exists "user" (
	id serial primary key,
	xid char(32) not null,
	name varchar(32) not null unique,
	key varchar(64) not null,
	salt varchar(32) not null,
	created timestamp not null default current_timestamp,
	updated timestamp not null default current_timestamp
);
