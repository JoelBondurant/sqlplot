drop table if exists "user";

create table if not exists "user" (
	id serial primary key,
	xid varchar(32) not null,
	name varchar(32) not null,
	key varchar(64) not null,
	salt varchar(32) not null,
	email varchar(64),
	phone varchar(16),
	created timestamp not null default current_timestamp,
	updated timestamp not null default current_timestamp
);
