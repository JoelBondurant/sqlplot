drop table if exists query;

create table if not exists query (
	id serial primary key,
	xid varchar(32) not null,
	connection_xid varchar(32) not null,
	name varchar(32) not null,
	query_text text not null
);
