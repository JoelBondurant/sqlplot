drop table if exists query;

create table if not exists query (
	id serial primary key,
	xid char(32) not null,
	user_xid char(32) not null,
	connection_xid char(32) not null,
	name varchar(32) not null,
	query_text text not null,
	created timestamp not null default current_timestamp,
	updated timestamp not null default current_timestamp
);
