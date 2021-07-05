drop table if exists "team";

create table if not exists "team" (
	id serial primary key,
	xid char(32) not null,
	name varchar(32) not null,
	created timestamp not null default current_timestamp,
	updated timestamp not null default current_timestamp
);
