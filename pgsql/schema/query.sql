drop table if exists "query" cascade;

create table if not exists "query" (
	xid char(32) primary key,
	user_xid char(32) not null,
	connection_xid char(32) not null,
	name varchar(32) not null,
	query_text text not null,
	created timestamp not null default current_timestamp,
	updated timestamp not null default current_timestamp,
	foreign key(user_xid) references "user"(xid)
);
